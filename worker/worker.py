import asyncio
import sys

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

import shared.shared_lib.logger_config  # noqa: F401 — loguru 핸들러 설정 적용
from loguru import logger
from shared.shared_lib.config import settings
from shared.shared_lib.database import get_session
from worker.caller.yfinance_caller import YFinanceCaller

# 실행 방법
# 스케줄 모드:  python -m worker.worker
# 수동 1회 실행: python -m worker.worker --once

async def collect_candles_job():
    """캔들 수집 job — 실행 1회당 세션 1개"""
    logger.info("Candle collection job started")
    async with get_session() as session:
        caller = YFinanceCaller(session)
        await caller.call()
    logger.info("Candle collection job finished")

async def main():
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        collect_candles_job,
        CronTrigger(
            hour=settings.COLLECT_CRON_HOUR,
            minute=settings.COLLECT_CRON_MINUTE,
            timezone="UTC",
        ),
        max_instances=1,         # 이전 실행이 안 끝났으면 중복 실행 금지
        coalesce=True,           # 밀린 실행은 1회로 합침
        misfire_grace_time=3600,
    )
    scheduler.start()
    logger.info(
        f"Scheduler started — candle collection daily at {settings.COLLECT_CRON_HOUR:02d}:{settings.COLLECT_CRON_MINUTE:02d} UTC"
    )
    await asyncio.Event().wait()  # 영구 대기

if __name__ == "__main__":
    if "--once" in sys.argv:
        asyncio.run(collect_candles_job())
    else:
        asyncio.run(main())
