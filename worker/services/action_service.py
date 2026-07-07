from decimal import Decimal

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from loguru import logger
from worker.repositories.action_repo import CorporateActionRepository

class ActionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CorporateActionRepository(db)

    async def save_actions(self, symbol: str, df: pd.DataFrame) -> int:
        """yfinance actions DataFrame(time/dividends/stock splits)을 증분 저장.
        마지막 저장 시각 이후의 이벤트만 insert — 신규 심볼은 전체 히스토리 백필"""
        rows = self._to_rows(symbol, df)
        if not rows:
            return 0

        last = await self.repo.get_last_time(symbol)
        if last is not None:
            rows = [r for r in rows if r["time"] > last]
        if not rows:
            return 0

        try:
            await self.repo.bulk_upsert(rows)
            await self.db.commit()
        except Exception:
            # aborted 트랜잭션이 세션에 남지 않도록 즉시 정리
            await self.db.rollback()
            raise

        logger.info(f"{symbol}: {len(rows)} new corporate actions saved")
        return len(rows)

    @staticmethod
    def _to_rows(symbol: str, df: pd.DataFrame) -> list[dict]:
        """배당/분할 컬럼을 (symbol, time, type, value) 행으로 변환 — 0인 값은 이벤트 아님"""
        if df.empty:
            return []

        # 같은 (time, type) 중복은 마지막 값 유지 (dict 덮어쓰기)
        dedup: dict[tuple, dict] = {}
        for _, row in df.iterrows():
            for col, action_type in (("dividends", "dividend"), ("stock splits", "split")):
                value = row.get(col)
                if value is None or pd.isna(value) or value == 0:
                    continue
                key = (row["time"], action_type)
                dedup[key] = {
                    "symbol": symbol,
                    "time": row["time"].to_pydatetime(),
                    "type": action_type,
                    "value": Decimal(str(value)),
                }
        return list(dedup.values())
