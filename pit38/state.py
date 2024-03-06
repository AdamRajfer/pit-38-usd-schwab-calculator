from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict


@dataclass
class AppState:
    exchange_rates: Dict[datetime, float] = field(default_factory=dict)
    stocks: Dict[str, float] = field(default_factory=dict)
