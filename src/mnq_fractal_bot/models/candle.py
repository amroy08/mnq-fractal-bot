from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int

    def __post_init__(self):
        if self.timestamp.tzinfo is None:
            raise ValueError("Candle timestamp must include a timezone.")

        if self.high < self.low:
            raise ValueError("Candle high cannot be below candle low.")

        if self.high < self.open or self.high < self.close:
            raise ValueError(
                "Candle high must be greater than or equal to open and close."
            )

        if self.low > self.open or self.low > self.close:
            raise ValueError(
                "Candle low must be less than or equal to open and close."
            )

        if self.volume < 0:
            raise ValueError("Candle volume cannot be negative.")