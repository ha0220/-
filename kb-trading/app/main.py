"""FastAPI 앱: 시세 조회 + 주문 + 계좌. 정적 프런트(static/)를 함께 서빙한다."""

from __future__ import annotations

import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .broker import Broker, BrokerError
from .config import Settings
from .kb_client import KBBroker
from .mock_broker import MockBroker
from .util import kst_now

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
CODE_RE = re.compile(r"^(?:[0-9A-Z]{6}|[0-9A-Z]{12})$")
ORDER_NO_RE = re.compile(r"^[0-9]{1,10}$")


def _norm_code(code: str) -> str:
    code = code.strip().upper()
    if not CODE_RE.match(code):
        raise ValueError("종목코드는 6자리 단축코드(예: 005930) 또는 12자리 표준코드여야 합니다.")
    return code


class OrderIn(BaseModel):
    side: Literal["buy", "sell"]
    code: str
    qty: int = Field(gt=0, le=100_000_000)
    price: int = Field(ge=0, le=1_000_000_000, default=0)
    order_type: Literal["limit", "market", "best", "priority"] = "limit"
    session: Literal["1", "2", "3"] = "1"  # 1 정규장, 2 장개시전 시간외종가, 3 장종료후 시간외종가
    sor: Literal["", "K", "N", "S"] = ""  # 거래소: 미지정/KRX/NXT/SOR
    confirm: bool = False

    _code = field_validator("code")(lambda cls, v: _norm_code(v))


class AmendIn(BaseModel):
    code: str
    qty: int = Field(gt=0, le=100_000_000)  # 정정 후 주문수량(= 미체결 잔량)
    price: int = Field(gt=0, le=1_000_000_000)
    order_type: Literal["limit"] = "limit"
    session: Literal["1", "2", "3"] = "1"
    sor: Literal["", "K", "N", "S"] = ""
    confirm: bool = False

    _code = field_validator("code")(lambda cls, v: _norm_code(v))


class CancelIn(BaseModel):
    code: str

    _code = field_validator("code")(lambda cls, v: _norm_code(v))


def create_app(settings: Settings | None = None, broker: Broker | None = None) -> FastAPI:
    cfg = settings or Settings.from_env()
    br: Broker = broker or (KBBroker(cfg) if cfg.is_live else MockBroker())

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        await br.aclose()

    app = FastAPI(title="KB 주식 매매", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    # DNS rebinding 방지: 허용된 Host 헤더만 받는다.
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(cfg.allowed_hosts))

    @app.middleware("http")
    async def same_origin_only(request: Request, call_next):
        # 다른 사이트에서 로컬 서버로 주문을 날리는 CSRF 차단
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            origin = request.headers.get("origin")
            if origin and urlparse(origin).netloc != request.headers.get("host"):
                return JSONResponse({"detail": "허용되지 않은 출처입니다."}, status_code=403)
        return await call_next(request)

    @app.exception_handler(BrokerError)
    async def broker_error(_: Request, exc: BrokerError):
        return JSONResponse({"detail": exc.message}, status_code=exc.status if exc.status in (401, 404, 422) else 502)

    def _valid_code(code: str) -> str:
        try:
            return _norm_code(code)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    def _strip_raw(d: dict, raw: bool) -> dict:
        return d if raw else {k: v for k, v in d.items() if k != "raw"}

    # ── 상태 ──
    @app.get("/api/status")
    async def status():
        return {"mode": cfg.mode, "trading_enabled": cfg.trading_enabled or not cfg.is_live,
                "max_order_amount": cfg.max_order_amount, "server_time": kst_now().isoformat(timespec="seconds")}

    # ── 시세 ──
    @app.get("/api/quote/{code}")
    async def quote(code: str, market: Literal["0", "1", "2"] = "1", raw: bool = Query(False)):
        return _strip_raw(await br.quote(_valid_code(code), market), raw and cfg.is_live)

    @app.get("/api/orderbook/{code}")
    async def orderbook(code: str, raw: bool = Query(False)):
        return _strip_raw(await br.orderbook(_valid_code(code)), raw and cfg.is_live)

    # ── 계좌 ──
    @app.get("/api/account/buying-power")
    async def buying_power():
        return await br.buying_power()

    @app.get("/api/account/portfolio")
    async def portfolio():
        return await br.portfolio()

    @app.get("/api/orders")
    async def orders():
        return {"orders": await br.orders()}

    # ── 주문 ──
    def _require_trading():
        if cfg.is_live and not cfg.trading_enabled:
            raise HTTPException(403, "실주문이 비활성화되어 있습니다. .env 에서 KB_TRADING_ENABLED=true 로 설정하세요.")

    async def _estimate(code: str, qty: int, price: int) -> int:
        if price > 0:
            return price * qty
        q = await br.quote(code)
        return q["price"] * qty

    @app.post("/api/orders")
    async def place_order(o: OrderIn):
        _require_trading()
        if not o.confirm:
            raise HTTPException(422, "주문 확인(confirm)이 필요합니다.")
        if o.order_type == "limit" and o.price <= 0:
            raise HTTPException(422, "지정가 주문은 가격이 필요합니다.")
        if o.order_type != "limit":
            o.price = 0
        amount = await _estimate(o.code[:6] if len(o.code) == 12 else o.code, o.qty, o.price)
        if amount > cfg.max_order_amount:
            raise HTTPException(422, f"1회 주문 한도({cfg.max_order_amount:,}원)를 초과합니다. 예상금액 {amount:,}원")
        res = await br.place_order(side=o.side, code=o.code, qty=o.qty, price=o.price,
                                   order_type=o.order_type, session=o.session, sor=o.sor)
        return {"ok": True, **res}

    @app.post("/api/orders/{order_no}/amend")
    async def amend_order(order_no: str, a: AmendIn):
        _require_trading()
        if not ORDER_NO_RE.match(order_no):
            raise HTTPException(422, "주문번호 형식이 올바르지 않습니다.")
        if not a.confirm:
            raise HTTPException(422, "주문 확인(confirm)이 필요합니다.")
        if a.price * a.qty > cfg.max_order_amount:
            raise HTTPException(422, f"1회 주문 한도({cfg.max_order_amount:,}원)를 초과합니다.")
        res = await br.amend_order(order_no=order_no, code=a.code, qty=a.qty, price=a.price,
                                   order_type=a.order_type, session=a.session, sor=a.sor)
        return {"ok": True, **res}

    @app.post("/api/orders/{order_no}/cancel")
    async def cancel_order(order_no: str, c: CancelIn):
        # 취소는 위험을 줄이는 동작이므로 KB_TRADING_ENABLED 와 무관하게 허용
        if not ORDER_NO_RE.match(order_no):
            raise HTTPException(422, "주문번호 형식이 올바르지 않습니다.")
        return {"ok": True, **await br.cancel_order(order_no=order_no, code=c.code)}

    # ── 정적 프런트 ──
    @app.get("/", include_in_schema=False)
    async def index():
        return FileResponse(STATIC_DIR / "index.html", headers={"Cache-Control": "no-store"})

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


def app_factory() -> FastAPI:  # uvicorn --factory app.main:app_factory
    return create_app()
