from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

@dataclass(frozen=True, slots=True)
class CandleData:
    """캔들 1개 — caller가 외부 API 응답을 정규화해 만드는 경계 DTO.

    외부 API(yfinance 등)에 대한 지식은 caller에서 끝나고,
    service 이후 레이어는 이 타입만 바라본다.
    time은 tz-aware UTC, 가격은 DB(Numeric)와 정밀도를 맞춘 Decimal.
    """
    time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
