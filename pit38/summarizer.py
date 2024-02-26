import sys
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
import yfinance as yf

from pit38.income import AnnualIncomeSummary, IncomeSummary
from pit38.schwab import SchwabAction
from pit38.utils import try_to_float


class Summarizer:
    def __init__(self) -> None:
        self.schwab_actions: Optional[List[SchwabAction]] = None
        self.exchange_rates: Optional[Dict[datetime, float]] = None
        self.schwab_buy_actions: Optional[List[SchwabAction]] = None
        self.summary: Optional[AnnualIncomeSummary] = None
        self.remaining: Optional[IncomeSummary] = None

    def load_schwab_actions(self, path: str) -> "Summarizer":
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
        self.schwab_actions = (
            df[::-1].apply(lambda x: SchwabAction(*x), axis=1).tolist()
        )
        return self

    def load_exchange_rates(self) -> "Summarizer":
        assert self.schwab_actions is not None
        df_list: List[pd.DataFrame] = []
        for year in set(
            [action.Date.year for action in self.schwab_actions]
            + [datetime.now().year]
        ):
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
        self.exchange_rates = (
            pd.concat(df_list).sort_index().shift()["_1USD"].to_dict()
        )
        return self

    def summarize_annual(self) -> "Summarizer":
        assert self.schwab_actions is not None
        schwab_buy_actions: List[SchwabAction] = []
        summary = AnnualIncomeSummary()
        for schwab_action in self.schwab_actions:
            error = False
            if schwab_action.Action == "Deposit":
                msg = self._buy(schwab_action, schwab_buy_actions)
            elif schwab_action.Action == "Sale":
                msg = self._sell(schwab_action, schwab_buy_actions, summary)
            elif schwab_action.Action == "Lapse":
                msg = f"{int(schwab_action.Quantity)} shares."
            elif schwab_action.Action in [
                "Wire Transfer",
                "Tax Withholding",
                "Dividend",
            ]:
                msg = f"{schwab_action.Amount:.2f} USD."
            else:
                msg = f"Unknown action! The summary may not be adequate."
                error = True
            msg = (
                f"[{schwab_action.Date.strftime('%Y-%m-%d')}]"
                f" {schwab_action.Action} ({schwab_action.Description}):"
                f" {msg}"
            )
            print(msg)
            if error:
                print(msg, file=sys.stderr)
        self.schwab_buy_actions = schwab_buy_actions
        self.summary = summary
        return self

    def calculate_remaining(self) -> "Summarizer":
        assert self.exchange_rates is not None
        assert self.schwab_buy_actions is not None
        curr_rate = self.exchange_rates[max(self.exchange_rates)]
        stocks = {}
        remaining = IncomeSummary()
        for share in self.schwab_buy_actions:
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
        self.remaining = remaining
        return self

    def to_frame(
        self, employment_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        assert self.summary is not None
        assert self.remaining is not None
        return self.summary.to_frame(self.remaining, employment_date)

    def _buy(
        self,
        schwab_action: SchwabAction,
        schwab_buy_actions: List[SchwabAction],
    ) -> str:
        assert self.exchange_rates is not None
        for _ in range(int(schwab_action.Quantity)):
            schwab_buy_actions.append(schwab_action)
        return f"{int(schwab_action.Quantity)} ESPP shares for {schwab_action.purchase_price * self.exchange_rates[schwab_action.Date] * int(schwab_action.Quantity):.2f} PLN."

    def _sell(
        self,
        schwab_action: SchwabAction,
        schwab_buy_actions: List[SchwabAction],
        summary: AnnualIncomeSummary,
    ) -> str:
        assert self.exchange_rates is not None
        msg = ""
        for _ in range(int(schwab_action.Shares)):
            schwab_buy_action = schwab_buy_actions.pop(0)
            income = (
                schwab_action.SalePrice
                * self.exchange_rates[schwab_action.Date]
            )
            cost = (
                schwab_buy_action.purchase_price
                * self.exchange_rates[schwab_buy_action.Date]
            )
            summary[schwab_action.Date.year] += IncomeSummary(income, cost)
            msg += f"\n  -> 1 {schwab_buy_action.Description} share for {income:.2f} PLN bought for {cost:.2f} PLN."
        return msg
