import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

import numpy as np
import pandas as pd
import yfinance as yf

from pit38.state import AppState


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
    app_state: Optional[AppState] = None
    year: int = field(init=False)
    quantity: int = field(init=False)
    shares: int = field(init=False)
    purchase_price: float = field(init=False)
    sale_price: float = field(init=False)
    current_sale_price: float = field(init=False)

    def __post_init__(self) -> None:
        self.app_state = self.app_state or AppState()
        self.year = self.Date.year
        self.quantity = 0 if pd.isnull(self.Quantity) else int(self.Quantity)
        self.shares = 0 if pd.isnull(self.Shares) else int(self.Shares)
        self.purchase_price = np.nan
        self.sale_price = np.nan
        self.current_sale_price = np.nan
        if (
            pd.notnull(self.Symbol)
            and self.Symbol not in self.app_state.stocks
        ):
            self.app_state.stocks[self.Symbol] = (
                yf.Ticker(self.Symbol).history(period="1d")["Close"].iloc[0]
            )

    def exchange(self) -> None:
        assert self.app_state is not None
        self.purchase_price = (
            0.0
            if pd.isnull(self.PurchasePrice)
            else self.PurchasePrice * self.app_state.exchange_rates[self.Date]
        )
        self.sale_price = (
            0.0
            if pd.isnull(self.SalePrice)
            else self.SalePrice * self.app_state.exchange_rates[self.Date]
        )
        self.current_sale_price = self.app_state.stocks[self.Symbol] * next(
            reversed(self.app_state.exchange_rates.values())
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
