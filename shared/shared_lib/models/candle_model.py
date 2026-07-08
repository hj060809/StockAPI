from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, DateTime, Numeric, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from shared.shared_lib.models.base import Base

class Candle(Base):
    """OHLCV 캔들 — auto_adjust=False 가격 저장, time은 UTC로 정규화

    주의: Yahoo는 auto_adjust=False여도 분할은 과거 전체에 소급 반영해 제공함.
    즉 저장 기준은 '분할 반영·배당 미반영' 가격. 배당 조정은 corporate_actions로
    조회 시점에 계산하고, 새 분할 발생 시엔 기존 행과 스케일이 어긋나므로
    수집 시 스케일 카나리아(candle_service.reconcile_scale)가 겹침 캔들 비교로
    감지해 재동기화함.

    복합 PK (symbol, timeframe, time)가 upsert의 ON CONFLICT 대상이자
    종목+주기 range scan / max(time) 조회 인덱스를 겸함.
    collection_tickers와 FK를 두지 않음 — 티커 제거/재등록이 데이터에 영향 없게.
    """
    __tablename__ = "candles"

    symbol: Mapped[str] = mapped_column(String(20), primary_key=True)
    timeframe: Mapped[str] = mapped_column(String(3), primary_key=True)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)

    open: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
