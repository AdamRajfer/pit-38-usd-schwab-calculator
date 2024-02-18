from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class IncomeSummary:
    gross: float = 0.0
    tax: float = field(init=False)
    net: float = field(init=False)

    def __post_init__(self) -> None:
        self.tax = self.gross * 0.19
        self.net = self.gross - self.tax

    def __add__(self, other: "IncomeSummary") -> "IncomeSummary":
        return IncomeSummary(self.gross + other.gross)


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
    _1THB: float
    _1USD: float
    _1AUD: float
    _1HKD: float
    _1CAD: float
    _1NZD: float
    _1SGD: float
    _1EUR: float
    _100HUF: float
    _1CHF: float
    _1GBP: float
    _1UAH: float
    _100JPY: float
    _1CZK: float
    _1DKK: float
    _100ISK: float
    _1NOK: float
    _1SEK: float
    _1RON: float
    _1BGN: float
    _1TRY: float
    _1ILS: float
    _100CLP: float
    _1PHP: float
    _1MXN: float
    _1ZAR: float
    _1BRL: float
    _1MYR: float
    _10000IDR: float
    _100INR: float
    _100KRW: float
    _1CNY: float
    _1XDR: float
    _1HRK: float
    _1RUB: float
