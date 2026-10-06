"""숫자 파싱·호가단위·종목코드 변환 유틸."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

KST = timezone(timedelta(hours=9))


def kst_now() -> datetime:
    return datetime.now(KST)


def to_int(value: Any, default: int = 0) -> int:
    """'  +00012,300 ' 같은 문자열을 정수로. 소수는 버림, 실패 시 default."""
    if value is None:
        return default
    s = str(value).strip().replace(",", "")
    if not s:
        return default
    try:
        return int(Decimal(s))
    except (InvalidOperation, ValueError):
        return default


def tick_size(price: int, etf: bool = False) -> int:
    """KRX 호가가격단위 (ETF/ETN은 5원)."""
    if etf:
        return 1 if price < 2000 else 5
    for limit, tick in ((2000, 1), (5000, 5), (20000, 10), (50000, 50), (200000, 100), (500000, 500)):
        if price < limit:
            return tick
    return 1000


def short_to_standard(code: str) -> str:
    """6자리 단축코드 -> 12자리 표준코드(KR7 + 코드 + 00 + 체크디지트). 이미 12자리면 그대로."""
    code = code.strip().upper()
    if len(code) == 12:
        return code
    base = f"KR7{code}00"
    digits = "".join(str(int(ch, 36)) for ch in base)
    total = 0
    for i, d in enumerate(reversed(digits)):
        n = int(d)
        if i % 2 == 0:
            n *= 2
            n = n // 10 + n % 10
        total += n
    return base + str((10 - total % 10) % 10)
