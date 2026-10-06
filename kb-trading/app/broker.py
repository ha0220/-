"""브로커 공통 인터페이스. KBBroker / MockBroker 모두 아래 '정규화된' 형태로 반환한다."""

from __future__ import annotations

from typing import Any, Protocol


class BrokerError(Exception):
    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.message = message
        self.status = status


# 주문유형 -> KB ordr_ccd
ORDER_TYPE_CODES = {"limit": "00", "market": "03", "best": "12", "priority": "13"}


class Broker(Protocol):
    name: str

    async def quote(self, code: str, market: str = "1") -> dict[str, Any]: ...
    async def orderbook(self, code: str) -> dict[str, Any]: ...
    async def buying_power(self) -> dict[str, Any]: ...
    async def portfolio(self) -> dict[str, Any]: ...
    async def orders(self) -> list[dict[str, Any]]: ...
    async def place_order(self, *, side: str, code: str, qty: int, price: int, order_type: str,
                          session: str, sor: str) -> dict[str, Any]: ...
    async def amend_order(self, *, order_no: str, code: str, qty: int, price: int, order_type: str,
                          session: str, sor: str) -> dict[str, Any]: ...
    async def cancel_order(self, *, order_no: str, code: str) -> dict[str, Any]: ...
    async def aclose(self) -> None: ...
