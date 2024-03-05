import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar, Dict, List

import numpy as np
import pandas as pd
import yfinance as yf


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
    year: int = field(init=False)
    quantity: int = field(init=False)
    shares: int = field(init=False)
    purchase_price: float = field(init=False)
    sale_price: float = field(init=False)
    current_sale_price: float = field(init=False)
    EXCHANGE_RATES: ClassVar[Dict[datetime, float]] = {}
    STOCKS: ClassVar[Dict[str, float]] = {}

    def __post_init__(self) -> None:
        self.year = self.Date.year
        self.quantity = 0 if pd.isnull(self.Quantity) else int(self.Quantity)
        self.shares = 0 if pd.isnull(self.Shares) else int(self.Shares)
        self.purchase_price = np.nan
        self.sale_price = np.nan
        self.current_sale_price = np.nan
        if pd.notnull(self.Symbol) and self.Symbol not in SchwabAction.STOCKS:
            SchwabAction.STOCKS[self.Symbol] = (
                yf.Ticker(self.Symbol).history(period="1d")["Close"].iloc[0]
            )

    def exchange(self) -> None:
        self.purchase_price = (
            0.0
            if pd.isnull(self.PurchasePrice)
            else self.PurchasePrice * SchwabAction.EXCHANGE_RATES[self.Date]
        )
        self.sale_price = (
            0.0
            if pd.isnull(self.SalePrice)
            else self.SalePrice * SchwabAction.EXCHANGE_RATES[self.Date]
        )
        self.current_sale_price = SchwabAction.STOCKS[self.Symbol] * next(
            reversed(SchwabAction.EXCHANGE_RATES.values())
        )

    @property
    def buying(self) -> bool:
        return self.Action == "Deposit"

    @property
    def selling(self) -> bool:
        return self.Action == "Sale"

    @property
    def lapsing(self) -> bool:
        return self.Action == "Lapse"

    @property
    def amounting(self) -> bool:
        return self.Action in ["Wire Transfer", "Tax Withholding", "Dividend"]

    def buy_msg(self) -> None:
        msg = f"{self.quantity} {self.Description} shares for {self.purchase_price * self.quantity:.2f} PLN."
        print(self._format_msg(msg))

    def sell_msg(self, sold_shares: List["SchwabAction"]) -> None:
        msg = ""
        for share in sold_shares:
            msg += f"\n  -> 1 {self.Type} share for {self.sale_price:.2f} PLN bought for {share.purchase_price:.2f} PLN."
        print(self._format_msg(msg))

    def lapse_msg(self) -> None:
        msg = f"{self.quantity} shares."
        print(self._format_msg(msg))

    def amount_msg(self) -> None:
        msg = f"{self.Amount:.2f} USD."
        print(self._format_msg(msg))

    def error_msg(self) -> None:
        msg = f"Unknown action! The summary may not be adequate."
        msg = self._format_msg(msg)
        print(msg)
        print(msg, file=sys.stderr)

    def _format_msg(self, msg: str) -> str:
        return f"[{self.Date.strftime('%Y-%m-%d')}] {self.Action} ({self.Description}): {msg}"
