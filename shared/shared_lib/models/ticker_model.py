from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from shared.shared_lib.models.base import Base

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

class CollectionTicker(Base):
    """수집 대상 티커 — API 서버에서 CRUD, 워커는 조회만"""
    __tablename__ = "collection_tickers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    symbol: Mapped[str] = mapped_column(String(20), nullable=False)          # 예: "AAPL"
    timeframe: Mapped[str] = mapped_column(String(3), nullable=False)       # Timeframe enum 값 (예: "1d")

    # False = 수집 중단 (soft delete — 이미 수집된 캔들은 보존)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # 보관 기간(일) — 수집 시 이보다 오래된 캔들은 삭제, fetch도 이 범위만 요청.
    # NULL = 무제한 (전체 기간 보관). 예: 일봉 3년치 = 1095, 분봉 7일치 = 7
    retention_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 마지막 수집 성공 시각 — 모니터링용. 증분 판단은 candles의 max(time)이 기준
    last_collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("symbol", "timeframe", name="uq_collection_tickers_symbol_timeframe"),
    )
