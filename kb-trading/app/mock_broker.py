"""자격증명 없이 화면/흐름을 확인하기 위한 모의 브로커 (실제 시세·주문과 무관한 가상 데이터)."""

from __future__ import annotations

import math
import time
import zlib
from typing import Any

from .broker import BrokerError
from .util import kst_now, tick_size

KNOWN = {
    "005930": ("삼성전자", 72000), "000660": ("SK하이닉스", 195000), "373220": ("LG에너지솔루션", 380000),
    "207940": ("삼성바이오로직스", 980000), "005380": ("현대차", 240000), "000270": ("기아", 110000),
    "035420": ("NAVER", 215000), "035720": ("카카오", 48000), "068270": ("셀트리온", 185000),
    "105560": ("KB금융", 88000), "055550": ("신한지주", 56000), "005490": ("POSCO홀딩스", 380000),
    "069500": ("KODEX 200", 36500), "102110": ("TIGER 200", 36400),
}


def _round_tick(price: float, etf: bool = False) -> int:
    t = tick_size(int(price), etf)
    return max(t, int(round(price / t)) * t)


class MockBroker:
    name = "mock"

    def __init__(self) -> None:
        self.cash = 10_000_000
        self.holdings: dict[str, dict[str, int]] = {"005930": {"qty": 10, "avg": 70000}}
        self._orders: list[dict[str, Any]] = []
        self._seq = 1000

    async def aclose(self) -> None:
        return None

    # ── 시세 (시간에 따라 천천히 움직이는 가상 가격) ─────────────────
    def _meta(self, code: str) -> tuple[str, int, bool]:
        if code in KNOWN:
            name, base = KNOWN[code]
            return name, base, "KODEX" in name or "TIGER" in name
        seed = zlib.crc32(code.encode())
        return f"모의종목 {code}", 5000 + (seed % 300) * 500, False

    def _price(self, code: str) -> tuple[int, int, bool, str]:
        name, base, etf = self._meta(code)
        seed = zlib.crc32(code.encode())
        wave = math.sin(time.time() / 45 + seed % 17) * 0.025 + math.sin(time.time() / 11 + seed % 7) * 0.005
        return _round_tick(base * (1 + wave), etf), base, etf, name

    async def quote(self, code: str, market: str = "1") -> dict[str, Any]:
        price, prev, etf, name = self._price(code)
        change = price - prev
        return {
            "code": code, "name": name, "market_name": "ETF" if etf else "KOSPI (모의)",
            "price": price, "prev_close": prev, "change": change, "rate": round(change / prev * 100, 2),
            "volume": 1_200_000 + zlib.crc32(code.encode()) % 900_000,
            "open": _round_tick(prev * 1.003, etf), "high": _round_tick(max(price, prev) * 1.01, etf),
            "low": _round_tick(min(price, prev) * 0.99, etf),
            "upper_limit": _round_tick(prev * 1.3, etf), "lower_limit": _round_tick(prev * 0.7, etf),
            "high_250": _round_tick(prev * 1.35, etf), "low_250": _round_tick(prev * 0.72, etf),
            "best_ask": price + tick_size(price, etf), "best_bid": price, "etf": etf,
        }

    async def orderbook(self, code: str) -> dict[str, Any]:
        price, _, etf, _ = self._price(code)
        t = tick_size(price, etf)
        bucket = int(time.time() // 3)
        seed = zlib.crc32(code.encode())

        def qty(n: int, side: int) -> int:
            return 50 + (zlib.crc32(f"{seed}:{bucket}:{n}:{side}".encode()) % 4000)

        asks = [{"level": n, "price": price + n * t, "qty": qty(n, 0)} for n in range(1, 11)]
        bids = [{"level": n, "price": price - (n - 1) * t, "qty": qty(n, 1)} for n in range(1, 11)]
        return {"code": code, "price": price, "asks": asks, "bids": bids,
                "total_ask_qty": sum(a["qty"] for a in asks), "total_bid_qty": sum(b["qty"] for b in bids)}

    # ── 계좌 ────────────────────────────────────────────────────────
    async def buying_power(self) -> dict[str, Any]:
        return {"deposit": self.cash, "cash_available": self.cash, "order_available": self.cash,
                "max_order_amount": self.cash}

    async def portfolio(self) -> dict[str, Any]:
        rows, cost_t, value_t = [], 0, 0
        for code, h in self.holdings.items():
            if h["qty"] <= 0:
                continue
            price, _, _, name = self._price(code)
            cost, value = h["avg"] * h["qty"], price * h["qty"]
            cost_t, value_t = cost_t + cost, value_t + value
            rows.append({"code": code, "name": name, "qty": h["qty"], "sellable_qty": h["qty"],
                         "avg_price": h["avg"], "price": price, "cost": cost, "value": value,
                         "pnl": value - cost, "pnl_rate": round((value - cost) / cost * 100, 2)})
        return {"rows": rows, "cost_total": cost_t, "value_total": value_t, "pnl_total": value_t - cost_t,
                "pnl_rate": round((value_t - cost_t) / cost_t * 100, 2) if cost_t else 0.0,
                "net_assets": value_t + self.cash}

    async def orders(self) -> list[dict[str, Any]]:
        for o in self._orders:
            if o["status"] in ("open", "partial"):
                self._try_fill(o)
        return sorted((dict(o) for o in self._orders), key=lambda o: o["order_no"], reverse=True)

    # ── 주문 ────────────────────────────────────────────────────────
    def _try_fill(self, o: dict[str, Any]) -> None:
        price, _, etf, _ = self._price(o["code"])
        t = tick_size(price, etf)
        ask, bid = price + t, price
        if o["side"] == "buy":
            exec_price = ask if o["order_type"] != "limit" or o["price"] >= ask else 0
        else:
            exec_price = bid if o["order_type"] != "limit" or o["price"] <= bid else 0
        if not exec_price:
            return
        qty = o["unfilled_qty"]
        if o["side"] == "buy":
            self.cash += (o["reserved"] - exec_price * qty) if o["reserved"] else -exec_price * qty
            h = self.holdings.setdefault(o["code"], {"qty": 0, "avg": 0})
            total = h["avg"] * h["qty"] + exec_price * qty
            h["qty"] += qty
            h["avg"] = total // h["qty"]
        else:
            self.cash += exec_price * qty
            self.holdings[o["code"]]["qty"] -= qty
        o.update(filled_qty=o["qty"], unfilled_qty=0, fill_price=exec_price, status="filled", reserved=0)

    def _new_order(self, side: str, code: str, qty: int, price: int, order_type: str) -> dict[str, Any]:
        cur, _, etf, name = self._price(code)
        ref = price if order_type == "limit" else cur + tick_size(cur, etf)
        if side == "buy":
            reserved = ref * qty
            if reserved > self.cash:
                raise BrokerError("주문가능금액이 부족합니다.", status=422)
            self.cash -= reserved
        else:
            held = self.holdings.get(code, {"qty": 0})["qty"]
            pending = sum(o["unfilled_qty"] for o in self._orders
                          if o["code"] == code and o["side"] == "sell" and o["status"] in ("open", "partial"))
            if qty > held - pending:
                raise BrokerError("매도 가능 수량이 부족합니다.", status=422)
            reserved = 0
        self._seq += 1
        return {"order_no": str(self._seq), "orig_order_no": "", "code": code, "name": name, "side": side,
                "side_name": "매수" if side == "buy" else "매도", "qty": qty, "filled_qty": 0,
                "unfilled_qty": qty, "price": price, "fill_price": 0, "time": kst_now().strftime("%H%M%S"),
                "order_type": order_type, "note": "", "status": "open", "reserved": reserved}

    async def place_order(self, *, side: str, code: str, qty: int, price: int, order_type: str,
                          session: str, sor: str) -> dict[str, Any]:
        o = self._new_order(side, code, qty, price, order_type)
        self._orders.append(o)
        self._try_fill(o)
        return {"order_no": o["order_no"], "message": "모의 주문이 접수되었습니다."}

    def _find_open(self, order_no: str) -> dict[str, Any]:
        for o in self._orders:
            if o["order_no"] == order_no and o["status"] in ("open", "partial"):
                return o
        raise BrokerError("정정/취소 가능한 주문을 찾을 수 없습니다.", status=404)

    async def cancel_order(self, *, order_no: str, code: str) -> dict[str, Any]:
        o = self._find_open(order_no)
        if o["side"] == "buy":
            self.cash += o["reserved"]
        o.update(status="cancel", note="취소", reserved=0, unfilled_qty=0)
        return {"order_no": order_no, "message": "모의 주문이 취소되었습니다."}

    async def amend_order(self, *, order_no: str, code: str, qty: int, price: int, order_type: str,
                          session: str, sor: str) -> dict[str, Any]:
        old = self._find_open(order_no)
        await self.cancel_order(order_no=order_no, code=code)
        res = await self.place_order(side=old["side"], code=old["code"], qty=qty, price=price,
                                     order_type=order_type, session=session, sor=sor)
        return res
