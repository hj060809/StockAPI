from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

@dataclass(frozen=True, slots=True)
class CorporateActionData:
    """기업행동(배당/분할) 1건 — caller가 외부 API 응답을 정규화해 만드는 경계 DTO.

    time은 ex-date의 tz-aware UTC.
    value는 dividend면 주당 배당금, split이면 분할 비율(예: 4:1 분할 = 4.0).
    """
    time: datetime
    type: Literal["dividend", "split"]
    value: Decimal
