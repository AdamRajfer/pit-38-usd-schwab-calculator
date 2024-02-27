from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import pandas as pd


@dataclass
class IncomeSummary:
    income: float = 0.0
    cost: float = 0.0
    gross: float = field(init=False)
    tax: float = field(init=False)
    net: float = field(init=False)

    def __post_init__(self) -> None:
        self.gross = self.income - self.cost
        self.tax = self.gross * 0.19
        self.net = self.gross - self.tax

    def __add__(self, other: "IncomeSummary") -> "IncomeSummary":
        return IncomeSummary(
            income=self.income + other.income, cost=self.cost + other.cost
        )


class AnnualIncomeSummary(defaultdict):
    def __init__(self) -> None:
        super().__init__(IncomeSummary)

    def to_frame(
        self, employment_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        df = pd.DataFrame({k: v.__dict__ for k, v in self.items()})
        df = df.assign(total=df.sum(axis=1))
        if employment_date is not None:
            months = (datetime.now() - employment_date).days / 30.4375
            df["total/month"] = df["total"] / months
        return df
