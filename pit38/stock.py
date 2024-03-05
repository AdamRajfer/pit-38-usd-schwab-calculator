from dataclasses import dataclass
from datetime import datetime
from typing import Dict

import numpy as np
import pandas as pd
import yfinance as yf

EXCHANGE_RATES: Dict[datetime, float] = {}
_STOCKS: Dict[str, float] = {}


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
    purchase_price: float = np.nan
    sale_price: float = np.nan
    current_sale_price: float = np.nan

    def exchange(self) -> None:
        self.purchase_price = (
            0.0
            if pd.isnull(self.PurchasePrice)
            else self.PurchasePrice * EXCHANGE_RATES[self.Date]
        )
        self.sale_price = (
            0.0
            if pd.isnull(self.SalePrice)
            else self.SalePrice * EXCHANGE_RATES[self.Date]
        )
        if self.Symbol not in _STOCKS:
            _STOCKS[self.Symbol] = (
                yf.Ticker(self.Symbol).history(period="1d")["Close"].iloc[0]
            )
        self.current_sale_price = _STOCKS[self.Symbol] * next(
            reversed(EXCHANGE_RATES.values())
        )
