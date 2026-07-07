import enum

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
