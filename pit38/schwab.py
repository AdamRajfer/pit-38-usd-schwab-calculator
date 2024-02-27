import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

import pandas as pd
import yfinance as yf

from pit38.income import AnnualIncomeSummary, IncomeSummary
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


class SchwabActions(list[SchwabAction]):
    @classmethod
    def load(cls, path: str) -> "SchwabActions":
        df = pd.read_csv(path)
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
        return cls(df[::-1].apply(lambda x: SchwabAction(*x), axis=1))

    def summarize(self, path: str) -> AnnualIncomeSummary:
        schwab_actions = SchwabActions.load(path)
        exchange_rates = schwab_actions.exchange_rates
        summary = AnnualIncomeSummary()
        for schwab_action in schwab_actions:
            name = schwab_action.Action
            desc = schwab_action.Description
            date = schwab_action.Date
            error = False
            if name == "Deposit":
                msg = self._buy(schwab_action, exchange_rates)
            elif name == "Sale":
                msg = self._sell(schwab_action, summary, exchange_rates)
            elif name == "Lapse":
                msg = f"{int(schwab_action.Quantity)} shares."
            elif name in ["Wire Transfer", "Tax Withholding", "Dividend"]:
                msg = f"{schwab_action.Amount:.2f} USD."
            else:
                msg = f"Unknown action! The summary may not be adequate."
                error = True
            msg = f"[{date.strftime('%Y-%m-%d')}] {name} ({desc}): {msg}"
            print(msg)
            if error:
                print(msg, file=sys.stderr)
        summary["remaining"] = self._remaining(exchange_rates)
        return summary

    def _buy(
        self, shares: SchwabAction, exchange_rates: Dict[datetime, float]
    ) -> str:
        quantity = int(shares.Quantity)
        for _ in range(quantity):
            self.append(shares)
        cost = shares.purchase_price * exchange_rates[shares.Date] * quantity
        return f"{quantity} ESPP shares for {cost:.2f} PLN."

    def _sell(
        self,
        shares: SchwabAction,
        summary: AnnualIncomeSummary,
        exchange_rates: Dict[datetime, float],
    ) -> str:
        msg = ""
        income = shares.SalePrice * exchange_rates[shares.Date]
        for _ in range(int(shares.Shares)):
            share = self.pop(0)
            cost = share.purchase_price * exchange_rates[share.Date]
            summary[shares.Date.year] += IncomeSummary(income, cost)
            msg += f"\n  -> 1 {share.Description} share for {income:.2f} PLN bought for {cost:.2f} PLN."
        return msg

    def _remaining(
        self, exchange_rates: Dict[datetime, float]
    ) -> IncomeSummary:
        curr_rate = exchange_rates[max(exchange_rates)]
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
