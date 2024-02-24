from dataclasses import dataclass, field
from datetime import datetime


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


@dataclass
class SchwabAction:
    Date: datetime
    Action: str
    Symbol: str
    Description: str
    Quantity: float
    FeesAndCommissions: float
    Amount: float
    Type: str
    Shares: float
    SalePrice: float
    GrantId: str
    VestDate: datetime
    VestFairMarketValue: float
    GrossProceeds: float
    AwardDate: datetime
    AwardId: str
    FairMarketValuePrice: float
    SharesSoldWithheldForTaxes: float
    NetSharesDeposited: float
    SubscriptionDate: datetime
    SubscriptionFairMarketValue: float
    PurchaseDate: datetime
    PurchasePrice: float
    PurchaseFairMarketValue: float
    DispositionType: str


@dataclass
class ExchangeRates:
    _1USD: float
