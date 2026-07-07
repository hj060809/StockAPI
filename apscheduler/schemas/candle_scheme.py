import enum
from typing import Sequence

class Timeframe(enum.Enum):
    MINUTE1 = '1m'
    MINUTE5 = '5m'
    MINUTE15 = '15m'
    MINUTE30 = '30m'
    HOUR1 = '1h'
    HOUR4 = '4h'
    HOUR12 = '12h'
    DAY1 = '1d'
    DAY3 = '3d'
    WEEK1 = '1w'
    WEEK2 = '2w'
    MONTH1 = '1M'
    MONTH3 = '3M'
    MONTH6 = '6M'
    YEAR1 = '1y'

class Candle:
    def __init__(self,
                 timestamp: int,
                 open: float,
                 high: float,
                 low: float,
                 close: float,
                 volume: float
                 ):
        self.timestamp = timestamp
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume


class Chart:
    def __init__(self, ticker: str, candles: Sequence[Candle], timeframe: Timeframe):
        self.ticker = ticker
        self.candles = candles
        self.timeframe = timeframe

    @property
    def period(self) -> int:
        if not self.candles:
            return 0
        return self.candles[-1].timestamp - self.candles[0].timestamp
