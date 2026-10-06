import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.kb_client import KBBroker
from app.main import create_app

HOSTS = ("localhost", "127.0.0.1", "[::1]", "testserver")


@pytest.fixture()
def client():
    app = create_app(Settings(mode="mock", allowed_hosts=HOSTS))
    with TestClient(app) as c:
        yield c


def test_quote_and_orderbook(client):
    q = client.get("/api/quote/005930").json()
    assert q["name"] == "삼성전자" and q["price"] > 0 and q["change"] == q["price"] - q["prev_close"]
    ob = client.get("/api/orderbook/005930").json()
    assert len(ob["asks"]) == len(ob["bids"]) == 10
    assert ob["asks"][0]["price"] > ob["bids"][0]["price"]


def test_invalid_code(client):
    assert client.get("/api/quote/12").status_code == 422


def test_buy_requires_confirm_and_respects_limit(client):
    body = {"side": "buy", "code": "005930", "qty": 1, "price": 0, "order_type": "market"}
    assert client.post("/api/orders", json=body).status_code == 422
    big = {**body, "qty": 1_000_000, "confirm": True}
    r = client.post("/api/orders", json=big)
    assert r.status_code == 422 and "한도" in r.json()["detail"]


def test_market_buy_fills_and_updates_portfolio(client):
    r = client.post("/api/orders", json={"side": "buy", "code": "000660", "qty": 2, "order_type": "market",
                                         "confirm": True})
    assert r.status_code == 200
    orders = client.get("/api/orders").json()["orders"]
    assert orders[0]["status"] == "filled" and orders[0]["side"] == "buy"
    rows = {p["code"]: p for p in client.get("/api/account/portfolio").json()["rows"]}
    assert rows["000660"]["qty"] == 2


def test_resting_limit_order_can_be_cancelled(client):
    q = client.get("/api/quote/005930").json()
    r = client.post("/api/orders", json={"side": "buy", "code": "005930", "qty": 1, "price": q["price"] // 2,
                                         "order_type": "limit", "confirm": True})
    no = r.json()["order_no"]
    assert client.get("/api/orders").json()["orders"][0]["status"] == "open"
    assert client.post(f"/api/orders/{no}/cancel", json={"code": "005930"}).status_code == 200
    assert client.get("/api/orders").json()["orders"][0]["status"] == "cancel"


def test_sell_more_than_held_rejected(client):
    r = client.post("/api/orders", json={"side": "sell", "code": "005930", "qty": 999, "order_type": "market",
                                         "confirm": True})
    assert r.status_code == 422


def test_cross_origin_post_blocked(client):
    r = client.post("/api/orders/1/cancel", json={"code": "005930"}, headers={"Origin": "https://evil.example"})
    assert r.status_code == 403


def test_bad_host_rejected():
    app = create_app(Settings(mode="mock"))
    with TestClient(app) as c:  # Host: testserver 는 허용 목록에 없음
        assert c.get("/api/status").status_code == 400


# ── KB 라이브 클라이언트: 요청 형식/정규화를 가짜 서버로 검증 ──────────────
def _kb(handler, **kw):
    s = Settings(mode="live", app_key="K" * 36, app_secret="S" * 32, trading_enabled=True, **kw)
    return s, KBBroker(s, transport=httpx.MockTransport(handler))


def test_kb_request_shape_and_quote_normalization():
    seen = []

    def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content)
        seen.append((req.url.path, dict(req.headers), body))
        if req.url.path == "/oauth2/token":
            return httpx.Response(200, json={"dataBody": {"access_token": "TOK", "expires_in": 86400}})
        return httpx.Response(200, json={"dataBody": {"is_nm": "삼성전자", "now_prc": "+000072000",
                                                      "bdy_cls_prc": "71000", "acml_vlm": "1,234"}})

    import asyncio
    _, kb = _kb(handler)
    q = asyncio.run(kb.quote("005930"))
    assert q["price"] == 72000 and q["change"] == 1000 and q["rate"] == 1.41 and q["volume"] == 1234
    path, headers, body = seen[1]
    assert path == "/api/v1/ivu10140"
    assert headers["authorization"] == "bearer TOK" and headers["appkey"] == "K" * 36
    assert body == {"dataHeader": {"ipAddr": "", "macAddr": ""}, "dataBody": {"excg_clsf": "1", "shrt_cd": "005930"}}


def test_kb_order_payload_and_failure_message():
    sent = []

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/oauth2/token":
            return httpx.Response(200, json={"dataBody": {"access_token": "TOK", "expires_in": 86400}})
        sent.append((req.url.path, json.loads(req.content)["dataBody"]))
        if len(sent) == 1:
            return httpx.Response(200, json={"dataBody": {"ordr_no": "0000123", "o_msg": "정상"}})
        return httpx.Response(200, json={"dataBody": {"ordr_no": "", "o_msg": "주문가능금액 부족"}})

    import asyncio
    _, kb = _kb(handler, order_code_mode="standard")
    ok = asyncio.run(kb.place_order(side="buy", code="005930", qty=3, price=71000, order_type="limit",
                                    session="1", sor=""))
    assert ok["order_no"] == "0000123"
    assert sent[0] == ("/api/v1/ssam1802", {"mkt_tm_clsf": "1", "is_cd": "KR7005930003", "ordr_q": "3",
                                           "ordr_uprc": "71000", "ordr_ccd": "00"})
    from app.broker import BrokerError
    with pytest.raises(BrokerError) as e:
        asyncio.run(kb.place_order(side="sell", code="005930", qty=1, price=0, order_type="market",
                                   session="1", sor="K"))
    assert "부족" in e.value.message and sent[1][0] == "/api/v1/ssam1801" and sent[1][1]["sor_ordr_ccd"] == "K"


def test_live_mode_blocks_orders_unless_enabled():
    from app.mock_broker import MockBroker  # 네트워크 없이 live 설정만 검증
    cfg = Settings(mode="live", app_key="K" * 36, app_secret="S" * 32, trading_enabled=False, allowed_hosts=HOSTS)
    with TestClient(create_app(cfg, broker=MockBroker())) as c:
        assert c.get("/api/status").json()["trading_enabled"] is False
        body = {"side": "buy", "code": "005930", "qty": 1, "order_type": "market", "confirm": True}
        r = c.post("/api/orders", json=body)
        assert r.status_code == 403 and "KB_TRADING_ENABLED" in r.json()["detail"]
        assert c.post("/api/orders/1/amend", json={"code": "005930", "qty": 1, "price": 100, "confirm": True}).status_code == 403
        # 취소는 위험 축소 동작이므로 차단하지 않는다 (여기선 없는 주문이라 404)
        assert c.post("/api/orders/1/cancel", json={"code": "005930"}).status_code == 404
