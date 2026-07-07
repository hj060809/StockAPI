from typing import Sequence

from shared.shared_lib.models.enums import Timeframe

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
