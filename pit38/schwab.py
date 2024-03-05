import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from functools import cached_property
from typing import Dict, Hashable, List, Optional

import pandas as pd
import yfinance as yf

from pit38.income import IncomeSummary
from pit38.utils import try_to_float


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

    @property
    def purchase_price(self) -> float:
        return 0.0 if pd.isnull(self.PurchasePrice) else self.PurchasePrice


class SchwabActionsFromFile(list[SchwabAction]):
    def __init__(self, path: str) -> None:
        super().__init__()
        self.path = path

    def load(self) -> "SchwabActionsFromFile":
        df = pd.read_csv(self.path)
        df["Date"] = pd.to_datetime(df["Date"])
        df_notnull = df[df["Date"].notna()].dropna(axis=1, how="all")
        curr = 0
        data = defaultdict(list)
        for i, row in df.iterrows():
            if pd.isna(row["Date"]):
                data[curr].append(row)
            else:
                if curr in data:
                    data[curr] = (
                        pd.DataFrame(data[curr])
                        .dropna(axis=1, how="all")
                        .assign(action_id=curr)
                    )
                curr = i
        if curr in data:
            data[curr] = (
                pd.DataFrame(data[curr])
                .dropna(axis=1, how="all")
                .assign(action_id=curr)
            )
        df_additional = (
            pd.concat(data.values())
            .dropna(axis=1, how="all")
            .set_index("action_id")
            .rename_axis(index=None)
        )
        df = df_notnull.join(df_additional)
        for col in df.columns:
            if "Date" in col:
                df[col] = pd.to_datetime(df[col])
        dolar_cols = (
            df.map(
                lambda x: ("$" in x if isinstance(x, str) else False) or None
            )
            .mean()
            .dropna()
            .index.tolist()
        )
        df[dolar_cols] = (
            df[dolar_cols]
            .map(
                lambda x: x.replace("$", "").replace(",", "") or None
                if isinstance(x, str)
                else x
            )
            .astype(float)
        )
        super().__init__(df[::-1].apply(lambda x: SchwabAction(**x), axis=1))
        return self

    @cached_property
    def exchange_rates(self) -> Dict[datetime, float]:
        df_list: List[pd.DataFrame] = []
        min_year = min(action.Date.year for action in self)
        for year in range(min_year, datetime.now().year + 1):
            df = (
                pd.read_csv(
                    f"https://static.nbp.pl/dane/kursy/Archiwum/archiwum_tab_a_{year}.csv",
                    delimiter=";",
                    encoding="iso-8859-2",
                    header=0,
                    skiprows=[1],
                )
                .set_index("data")
                .map(try_to_float)
                .dropna(axis=1, how="all")
                .dropna(axis=0, how="all")
                .astype(float)
                .rename_axis(index="Date")
            )
            df.index = pd.to_datetime(df.index)
            df.columns = [f"_{x}" if x[0].isdigit() else x for x in df.columns]
            df_list.append(df)
        return pd.concat(df_list).sort_index().shift()["_1USD"].to_dict()


class SchwabActions(list[SchwabAction]):
    def __init__(
        self, path: str, employment_date: Optional[datetime] = None
    ) -> None:
        self.schwab_actions_from_file = SchwabActionsFromFile(path)
        self.employment_date = employment_date
        self.summary: Dict[Hashable, IncomeSummary] = defaultdict(
            IncomeSummary
        )

    def prepare_summary(self) -> "SchwabActions":
        for action in self.schwab_actions_from_file.load():
            name = action.Action
            desc = action.Description
            date = action.Date
            error = False
            if name == "Deposit":
                msg = self._buy(action)
            elif name == "Sale":
                msg = self._sell(action)
            elif name == "Lapse":
                msg = f"{int(action.Quantity)} shares."
            elif name in ["Wire Transfer", "Tax Withholding", "Dividend"]:
                msg = f"{action.Amount:.2f} USD."
            else:
                msg = f"Unknown action! The summary may not be adequate."
                error = True
            msg = f"[{date.strftime('%Y-%m-%d')}] {name} ({desc}): {msg}"
            print(msg)
            if error:
                print(msg, file=sys.stderr)
        self.summary["remaining"] = self.remaining
        return self

    def to_html(self) -> str:
        df = pd.DataFrame({k: v.__dict__ for k, v in self.summary.items()})
        df = df.assign(total=df.sum(axis=1))
        if self.employment_date is not None:
            months = (datetime.now() - self.employment_date).days / 30.4375
            df["total/month"] = df["total"] / months
        return (
            df.style.format("{:,.2f}")
            .set_table_styles(
                [{"selector": "th, td", "props": [("text-align", "right")]}],
                overwrite=False,
            )
            .to_html()
        )

    def _buy(self, shares: SchwabAction) -> str:
        quantity = int(shares.Quantity)
        for _ in range(quantity):
            self.append(shares)
        cost = (
            shares.purchase_price * self.exchange_rates[shares.Date] * quantity
        )
        return f"{quantity} ESPP shares for {cost:.2f} PLN."

    def _sell(self, shares: SchwabAction) -> str:
        msg = ""
        income = shares.SalePrice * self.exchange_rates[shares.Date]
        for _ in range(int(shares.Shares)):
            share = self.pop(0)
            cost = share.purchase_price * self.exchange_rates[share.Date]
            self.summary[shares.Date.year] += IncomeSummary(income, cost)
            msg += f"\n  -> 1 {share.Description} share for {income:.2f} PLN bought for {cost:.2f} PLN."
        return msg

    @property
    def remaining(self) -> IncomeSummary:
        curr_rate = self.exchange_rates[max(self.exchange_rates)]
        stocks = {}
        remaining = IncomeSummary()
        for share in self:
            if share.Symbol not in stocks:
                stocks[share.Symbol] = (
                    yf.Ticker(share.Symbol)
                    .history(period="1d")["Close"]
                    .iloc[0]
                )
            remaining += IncomeSummary(
                income=stocks[share.Symbol] * curr_rate,
                cost=share.purchase_price,
            )
        return remaining

    @property
    def exchange_rates(self) -> Dict[datetime, float]:
        return self.schwab_actions_from_file.exchange_rates
