from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict


@dataclass
class AppState:
    exchange_rates: Dict[datetime, float] = field(default_factory=dict)
    stocks: Dict[str, float] = field(default_factory=dict)

    def exchange_rate(self, date: datetime) -> float:
        if date in self.exchange_rates:
            return self.exchange_rates[date]
        date = sorted(filter(lambda x: x < date, self.exchange_rates))[-1]
        return self.exchange_rates[date]
