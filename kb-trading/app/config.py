"""환경변수 기반 설정."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    mode: str = "mock"  # "mock" | "live"
    base_url: str = "https://developer.kbsec.com:32484"
    app_key: str = field(default="", repr=False)
    app_secret: str = field(default="", repr=False)
    trading_enabled: bool = False
    max_order_amount: int = 5_000_000
    order_code_mode: str = "short"  # "short" | "standard"
    allowed_hosts: tuple[str, ...] = ("localhost", "127.0.0.1", "[::1]")

    @property
    def is_live(self) -> bool:
        return self.mode == "live"

    @classmethod
    def from_env(cls) -> "Settings":
        app_key = os.environ.get("KB_OPENAPI_APP_KEY", "").strip()
        app_secret = os.environ.get("KB_OPENAPI_APP_SECRET", "").strip()
        mode = os.environ.get("KB_MODE", "").strip().lower() or ("live" if app_key and app_secret else "mock")
        if mode not in {"mock", "live"}:
            raise RuntimeError("KB_MODE 는 mock 또는 live 여야 합니다.")
        if mode == "live" and not (app_key and app_secret):
            raise RuntimeError("live 모드에는 KB_OPENAPI_APP_KEY / KB_OPENAPI_APP_SECRET 이 필요합니다.")
        code_mode = os.environ.get("KB_ORDER_CODE_MODE", "short").strip().lower()
        if code_mode not in {"short", "standard"}:
            raise RuntimeError("KB_ORDER_CODE_MODE 는 short 또는 standard 여야 합니다.")
        extra = tuple(h.strip() for h in os.environ.get("KB_ALLOWED_HOSTS", "").split(",") if h.strip())
        return cls(
            mode=mode,
            base_url=os.environ.get("KB_OPENAPI_BASE_URL", cls.base_url).rstrip("/"),
            app_key=app_key,
            app_secret=app_secret,
            trading_enabled=_bool("KB_TRADING_ENABLED", False),
            max_order_amount=int(os.environ.get("KB_MAX_ORDER_AMOUNT", "5000000")),
            order_code_mode=code_mode,
            allowed_hosts=cls.allowed_hosts + extra,
        )
