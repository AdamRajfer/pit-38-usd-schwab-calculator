from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd


@dataclass
class SchwabAction:
    Date: datetime = pd.NaT
    Action: str = ""
    Symbol: str = ""
    Description: str = ""
    Quantity: float = np.nan
    FeesAndCommissions: float = np.nan
    DisbursementElection: str = ""
    Amount: float = np.nan
    Type: str = ""
    Shares: float = np.nan
    SalePrice: float = np.nan
    SubscriptionDate: datetime = pd.NaT
    SubscriptionFairMarketValue: float = np.nan
    PurchaseDate: datetime = pd.NaT
    PurchasePrice: float = np.nan
    PurchaseFairMarketValue: float = np.nan
    DispositionType: str = ""
    GrantId: str = ""
    VestDate: datetime = pd.NaT
    VestFairMarketValue: float = np.nan
    GrossProceeds: float = np.nan
    AwardDate: datetime = pd.NaT
    AwardId: str = ""
    FairMarketValuePrice: float = np.nan
    SharesSoldWithheldForTaxes: float = np.nan
    NetSharesDeposited: float = np.nan
    Taxes: float = np.nan


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
            income=self.income + other.income,
            cost=self.cost + other.cost,
        )
