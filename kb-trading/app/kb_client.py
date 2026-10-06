"""KB증권 OpenAPI(B2C, 운영) 클라이언트.

규칙(샘플코드 example/python 과 동일):
  - POST {base}/oauth2/token  (client_credentials) -> dataBody.access_token
  - POST {base}/api/v1/<tr>   헤더: appKey, Authorization: bearer <token>
    본문: {"dataHeader": {"ipAddr","macAddr"}, "dataBody": {...}}
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from .broker import ORDER_TYPE_CODES, BrokerError
from .config import Settings
from .util import kst_now, short_to_standard, to_int

TOKEN_SAFETY_MARGIN = 300  # 만료 5분 전에 재발급


class KBBroker:
    name = "live"

    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self.s = settings
        self._http = httpx.AsyncClient(base_url=settings.base_url, timeout=10.0, transport=transport)
        self._token: str | None = None
        self._token_exp = 0.0
        self._lock = asyncio.Lock()

    async def aclose(self) -> None:
        await self._http.aclose()

    # ── 인증 / 공통 호출 ────────────────────────────────────────────
    async def _get_token(self, force: bool = False) -> str:
        async with self._lock:
            if not force and self._token and time.time() < self._token_exp:
                return self._token
            body = {
                "dataHeader": {"ipAddr": "", "macAddr": ""},
                "dataBody": {"appKey": self.s.app_key, "appSecret": self.s.app_secret,
                             "grantType": "client_credentials"},
            }
            data = await self._post("/oauth2/token", {"Content-Type": "application/json"}, body)
            db = data.get("dataBody", data)
            token = db.get("access_token") or db.get("accessToken")
            if not token:
                raise BrokerError(f"토큰 발급 실패: {_message(data) or '응답에 access_token 없음'}")
            self._token = token
            self._token_exp = time.time() + max(60, to_int(db.get("expires_in"), 3600) - TOKEN_SAFETY_MARGIN)
            return token

    async def _post(self, path: str, headers: dict[str, str], body: dict[str, Any]) -> dict[str, Any]:
        try:
            r = await self._http.post(path, headers=headers, json=body)
        except httpx.HTTPError as exc:
            raise BrokerError(f"KB증권 서버 연결 실패: {type(exc).__name__}") from exc
        try:
            data = r.json()
        except ValueError:
            data = {}
        if r.status_code == 401:
            raise BrokerError(_message(data) or "인증 실패(401)", status=401)
        if r.status_code >= 400:
            raise BrokerError(_message(data) or f"KB증권 API 오류 (HTTP {r.status_code})")
        if not isinstance(data, dict):
            raise BrokerError("KB증권 API가 JSON 객체가 아닌 응답을 반환했습니다.")
        return data

    async def _call(self, tr: str, data_body: dict[str, Any], _retry: bool = True) -> dict[str, Any]:
        token = await self._get_token()
        headers = {"Content-Type": "application/json", "appKey": self.s.app_key,
                   "Authorization": f"bearer {token}"}
        body = {"dataHeader": {"ipAddr": "", "macAddr": ""}, "dataBody": data_body}
        try:
            data = await self._post(f"/api/v1/{tr}", headers, body)
        except BrokerError as exc:
            if exc.status == 401 and _retry:
                await self._get_token(force=True)
                return await self._call(tr, data_body, _retry=False)
            raise
        return data.get("dataBody", data)

    # ── 시세 ────────────────────────────────────────────────────────
    async def quote(self, code: str, market: str = "1") -> dict[str, Any]:
        b = await self._call("ivu10140", {"excg_clsf": market, "shrt_cd": code})
        if "now_prc" not in b:
            raise BrokerError(_message(b) or "현재가 응답이 비어 있습니다. 종목코드를 확인하세요.", status=404)
        prev = abs(to_int(b.get("bdy_cls_prc"))) or abs(to_int(b.get("sprc")))
        price = abs(to_int(b["now_prc"])) or prev
        change = price - prev if prev else 0
        return {
            "code": code,
            "name": (b.get("is_nm") or "").strip(),
            "market_name": (b.get("mkt_clsf_nm") or "").strip(),
            "price": price,
            "prev_close": prev,
            "change": change,
            "rate": round(change / prev * 100, 2) if prev else 0.0,
            "volume": to_int(b.get("acml_vlm")),
            "open": abs(to_int(b.get("opn_prc"))),
            "high": abs(to_int(b.get("hgh_prc"))),
            "low": abs(to_int(b.get("lw_prc"))),
            "upper_limit": abs(to_int(b.get("ulmt_prc"))),
            "lower_limit": abs(to_int(b.get("llmt_prc"))),
            "high_250": abs(to_int(b.get("dy250_max_prc"))),
            "low_250": abs(to_int(b.get("dy250_min_prc"))),
            "best_ask": abs(to_int(b.get("s_sq1_askprc"))),
            "best_bid": abs(to_int(b.get("b_sq1_askprc"))),
            "etf": "ETF" in (b.get("mkt_clsf_nm") or "").upper() or "ETN" in (b.get("mkt_clsf_nm") or "").upper(),
            "raw": b,
        }

    async def orderbook(self, code: str) -> dict[str, Any]:
        b = await self._call("ivu10070", {"is_cd": code, "ovtm_mkt_clsf": "0"})
        if "s1_aprc" not in b:
            raise BrokerError(_message(b) or "호가 응답이 비어 있습니다.", status=404)
        asks, bids = [], []
        for n in range(1, 11):
            # '매도위치/매수위치' 수량 필드 중 해당 호가 쪽 필드를 우선 사용 (문서상 의미 추정, README 참고)
            ask_q = to_int(b.get(f"s_pstn_s{n}_aprc_q")) or to_int(b.get(f"b_pstn_s{n}_aprc_q"))
            bid_q = to_int(b.get(f"b_pstn_b{n}_aprc_q")) or to_int(b.get(f"s_pstn_b{n}_aprc_q"))
            asks.append({"level": n, "price": abs(to_int(b.get(f"s{n}_aprc"))), "qty": ask_q})
            bids.append({"level": n, "price": abs(to_int(b.get(f"b{n}_aprc"))), "qty": bid_q})
        return {
            "code": code,
            "price": abs(to_int(b.get("now_prc"))),
            "asks": asks,
            "bids": bids,
            "total_ask_qty": to_int(b.get("s_askprc_tl_q")),
            "total_bid_qty": to_int(b.get("b_askprc_tl_q")),
            "raw": b,
        }

    # ── 계좌 ────────────────────────────────────────────────────────
    async def buying_power(self) -> dict[str, Any]:
        b = await self._call("ssqm1802", {})
        return {
            "deposit": to_int(b.get("tfnd")),
            "cash_available": to_int(b.get("ordr_psbl_csh")),
            "order_available": to_int(b.get("ordr_psbl_tl_amt")),
            "max_order_amount": to_int(b.get("mx_ordr_psbl_amt")),
        }

    async def portfolio(self) -> dict[str, Any]:
        b = await self._call("ssqm2952", {})
        rows = []
        for r in b.get("Record1") or []:
            qty = to_int(r.get("hld_q"))
            if qty <= 0 and not (r.get("is_cd") or "").strip():
                continue
            cost, value = to_int(r.get("byng_amt")), to_int(r.get("val_amt"))
            pl = to_int(r.get("val_pl"), value - cost)
            rows.append({
                "code": (r.get("is_cd") or "").strip(),
                "name": (r.get("is_nm") or "").strip(),
                "qty": qty,
                "sellable_qty": to_int(r.get("ordr_psbl_q")),
                "avg_price": to_int(r.get("byng_avr_prc")),
                "price": abs(to_int(r.get("now_prc"))),
                "cost": cost,
                "value": value,
                "pnl": pl,
                "pnl_rate": round(pl / cost * 100, 2) if cost else 0.0,
            })
        cost_sum, value_sum = to_int(b.get("byng_amt_sum")), to_int(b.get("val_amt_sum"))
        pl_sum = to_int(b.get("val_pl_sum"), value_sum - cost_sum)
        return {
            "rows": rows,
            "cost_total": cost_sum,
            "value_total": value_sum,
            "pnl_total": pl_sum,
            "pnl_rate": round(pl_sum / cost_sum * 100, 2) if cost_sum else 0.0,
            "net_assets": to_int(b.get("nt_asts_val_amt")),
        }

    async def orders(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        nxt, today = "", kst_now().strftime("%Y%m%d")
        for _ in range(5):  # 연속조회 최대 5페이지
            b = await self._call("ssqm2341", {"ccls_clsf": "0", "ordr_dt": today, "nxt_key": nxt})
            for r in b.get("Record1") or []:
                out.append(_normalize_order(r))
            new_key = (b.get("nxt_key") or "").strip()
            if not new_key or new_key == nxt or not b.get("Record1"):
                break
            nxt = new_key
        out.sort(key=lambda o: (o["time"], o["order_no"]), reverse=True)
        return out

    # ── 주문 ────────────────────────────────────────────────────────
    def _code(self, code: str) -> str:
        return short_to_standard(code) if self.s.order_code_mode == "standard" else code

    async def place_order(self, *, side: str, code: str, qty: int, price: int, order_type: str,
                          session: str, sor: str) -> dict[str, Any]:
        tr = "ssam1802" if side == "buy" else "ssam1801"
        body = {"mkt_tm_clsf": session, "is_cd": self._code(code), "ordr_q": str(qty),
                "ordr_uprc": str(price), "ordr_ccd": ORDER_TYPE_CODES[order_type]}
        if sor:
            body["sor_ordr_ccd"] = sor
        return _order_result(await self._call(tr, body))

    async def amend_order(self, *, order_no: str, code: str, qty: int, price: int, order_type: str,
                          session: str, sor: str) -> dict[str, Any]:
        body = {"mkt_tm_clsf": session, "is_cd": self._code(code) if len(code) == 6 else code,
                "ordr_q": str(qty), "ordr_uprc": str(price), "ordr_ccd": ORDER_TYPE_CODES[order_type],
                "crct_clsf": "2", "orgn_ordr_no": order_no}
        if sor:
            body["sor_ordr_ccd"] = sor
        return _order_result(await self._call("ssam1805", body))

    async def cancel_order(self, *, order_no: str, code: str) -> dict[str, Any]:
        body = {"is_cd": self._code(code) if len(code) == 6 else code,
                "crct_clsf": "2", "orgn_ordr_no": order_no}
        return _order_result(await self._call("ssam1806", body))


def _message(data: Any) -> str:
    """응답 어디에 있든 사람이 읽을 메시지(o_msg/msg/message)를 찾는다."""
    if isinstance(data, dict):
        for key in ("o_msg", "msg", "message", "msg1"):
            v = data.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
        for v in data.values():
            if isinstance(v, dict):
                found = _message(v)
                if found:
                    return found
    return ""


def _order_result(b: dict[str, Any]) -> dict[str, Any]:
    order_no = (b.get("ordr_no") or "").strip()
    if not order_no or to_int(order_no, -1) == 0:
        raise BrokerError(_message(b) or "주문이 접수되지 않았습니다(주문번호 없음).", status=422)
    return {"order_no": order_no, "message": _message(b) or "주문이 접수되었습니다."}


def _normalize_order(r: dict[str, Any]) -> dict[str, Any]:
    qty, filled, unfilled = to_int(r.get("ordr_q")), to_int(r.get("tl_ccls_q")), to_int(r.get("nccls_q"))
    side_name = (r.get("trd_dl_ccd_nm") or "").strip()
    note = (r.get("rfsl_rsn_nm") or "").strip() or (r.get("crct_cncl_ccd") or "").strip()
    if (r.get("rfsl_rsn_nm") or "").strip():
        status = "rejected"
    elif "취소" in note:
        status = "cancel"
    elif unfilled > 0:
        status = "partial" if filled > 0 else "open"
    else:
        status = "filled" if filled > 0 else "done"
    t = (r.get("ordr_tm") or r.get("ccls_ntc_tm") or "").strip()
    return {
        "order_no": (r.get("ordr_no") or "").strip(),
        "orig_order_no": (r.get("orgn_ordr_no") or "").strip(),
        "code": (r.get("stnd_is_no") or "").strip(),
        "name": (r.get("hngl_shrt_nm") or "").strip(),
        "side": "buy" if "매수" in side_name else "sell" if "매도" in side_name else "",
        "side_name": side_name,
        "qty": qty,
        "filled_qty": filled,
        "unfilled_qty": unfilled,
        "price": to_int(r.get("ordr_uprc")),
        "fill_price": to_int(r.get("ccls_uprc")),
        "time": t,
        "order_type": (r.get("ordr_typ_cd") or "").strip(),
        "note": note,
        "status": status,
    }
