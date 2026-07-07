from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, DateTime, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from shared.shared_lib.models.base import Base

class CorporateAction(Base):
    """기업행동(배당/분할) — 수정주가 계산의 원천 데이터

    원시 candles는 불변으로 유지하고, 조회 시점에 이 테이블로 누적 조정 팩터를
    계산해 적용한다 (분할: ex-date 이전 가격 × 1/비율, 배당: × (1 - 배당금/직전종가)).
    심볼 단위 데이터라 timeframe 구분 없음. retention 정책과 무관하게 전체 보관.
    """
    __tablename__ = "corporate_actions"

    symbol: Mapped[str] = mapped_column(String(20), primary_key=True)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)  # ex-date, UTC
    type: Mapped[str] = mapped_column(String(10), primary_key=True)  # 'dividend' | 'split'

    # dividend: 주당 배당금, split: 분할 비율 (예: 4:1 분할 = 4.0)
    value: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
