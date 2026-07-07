from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
import requests_cache
import yfinance as yf
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

from apscheduler.services.candle_service import CandleService

class CandleCaller:
    def __init__(
            self,
            db: AsyncSession
    ):
        self.service = CandleService(db)

    async def call(
        self,
        tickers: Sequence[str],
    ):
        raise NotImplementedError

class YFinanceCaller(CandleCaller):
    def __init__(
            self,
            db: AsyncSession,
            sessionCachePath: str = 'app/data/yfinance.cache',
    ):
        super().__init__(db)
        self.cached_session = requests_cache.CachedSession(
            cache_name=sessionCachePath,
            backend='sqlite',
            expire_after=60,
        )

        self.cached_session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def fetch_data(self, ticker: str, interval: str):
        try:
            data = yf.Ticker(ticker, session=self.cached_session)
            df = data.history(period="5d", interval=interval)
            
            if df.empty:
                return pd.DataFrame()
            
            df = df.reset_index()
            df.columns = [c.lower() for c in df.columns]
            df["ticker"] = ticker
            df["interval"] = interval
            df = df.rename(columns={"datetime": "time", "date": "time"})
            return df[["time", "ticker", "open", "high", "low", "close", "volume", "interval"]]
        
        except Exception as e:
            logger.error(f"{ticker} 실패: {e}")
            return pd.DataFrame()

    def call(
        self,
        tickers: Sequence[str],
        interval: str
    ):
        frames = []

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(self.fetch_data, t, interval): t for t in tickers}

            for future in as_completed(futures):
                df = future.result()
                if not df.empty:
                    frames.append(df)

        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()