from collections import defaultdict
from datetime import datetime
from functools import cached_property
from typing import Dict, List

import pandas as pd
import yfinance as yf

from pit_38_usd_schwab_calculator.config import (
    ExchangeRates,
    IncomeSummary,
    SchwabAction,
)
from pit_38_usd_schwab_calculator.config_store import Config
from pit_38_usd_schwab_calculator.utils import try_to_float


class Pit38USDSchwabCalculator:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.schwab_buy_actions: List[SchwabAction] = []

    def summarize(self) -> None:
        df = pd.DataFrame(
            {k: v.__dict__ for k, v in self.annual_income_summary.items()}
        )
        total = df.sum(axis=1).to_frame("total").T
        months = (
            datetime.now() - pd.to_datetime(self.config.employment_date)
        ).days / 30
        total["remaining_gross"] = self.remaining
        total["remaining_tax"] = total["remaining_gross"] * 0.19
        total["remaining_net"] = (
            total["remaining_gross"] - total["remaining_tax"]
        )
        total["(gross + remaining_gross + salary_gross) / month"] = (
            total["gross"] / months
            + total["remaining_gross"] / months
            + self.config.salary_gross_per_month
        )
        total["(net + remaining_net + salary_net) / month"] = (
            total["net"] / months
            + total["remaining_net"] / months
            + self.config.salary_net_per_month
        )
        df = df.join(total.T, how="right")
        print(df.to_string())

    @cached_property
    def annual_income_summary(self) -> Dict[int, IncomeSummary]:
        annual_income_summary: Dict[int, IncomeSummary] = defaultdict(
            IncomeSummary
        )
        for schwab_action in self.schwab_actions:
            if schwab_action.Description == "ESPP":
                for _ in range(int(schwab_action.Quantity)):
                    self.schwab_buy_actions.append(schwab_action)
                msg = f"{self.config.format_config.espp}{int(schwab_action.Quantity)} ESPP shares\033[0m for {schwab_action.PurchasePrice * self.exchange_rates[schwab_action.Date]._1USD * int(schwab_action.Quantity):.2f} PLN."
            elif schwab_action.Type == "ESPP":
                msg = ""
                for _ in range(int(schwab_action.Shares)):
                    sold_share = self.schwab_buy_actions.pop(0)
                    annual_income_summary[
                        schwab_action.Date.year
                    ] += IncomeSummary(
                        schwab_action.SalePrice
                        * self.exchange_rates[schwab_action.Date]._1USD
                        - sold_share.PurchasePrice
                        * self.exchange_rates[sold_share.Date]._1USD
                    )
                    msg += f"\n  -> {getattr(self.config.format_config, sold_share.Description.lower())}1 {sold_share.Description} share\033[0m for {schwab_action.SalePrice * self.exchange_rates[schwab_action.Date]._1USD:.2f} PLN bought for {sold_share.PurchasePrice * self.exchange_rates[sold_share.Date]._1USD:.2f} PLN."
            elif schwab_action.Description == "RS":
                for _ in range(int(schwab_action.Quantity)):
                    self.schwab_buy_actions.append(schwab_action)
                msg = f"{self.config.format_config.rs}{int(schwab_action.Quantity)} RS shares\033[0m."
            elif schwab_action.Type == "RS":
                msg = ""
                for _ in range(int(schwab_action.Shares)):
                    sold_share = self.schwab_buy_actions.pop(0)
                    annual_income_summary[
                        schwab_action.Date.year
                    ] += IncomeSummary(
                        schwab_action.SalePrice
                        * self.exchange_rates[schwab_action.Date]._1USD
                    )
                    msg += f"\n  -> {getattr(self.config.format_config, sold_share.Description.lower())}1 {sold_share.Description} share\033[0m for {schwab_action.SalePrice * self.exchange_rates[schwab_action.Date]._1USD:.2f} PLN."
            elif schwab_action.Description == "Cash Disbursement":
                msg = f"\033[0;32m{-schwab_action.Amount:.2f} USD\033[0m. Included fees and commissions \033[1;31m{-schwab_action.FeesAndCommissions:.2f} USD\033[0m."
            elif schwab_action.Description == "Debit":
                msg = f"\033[1;31m{-schwab_action.Amount:.2f} USD\033[0m."
            elif schwab_action.Description == "Credit":
                msg = f"\033[0;32m{schwab_action.Amount:.2f} USD\033[0m."
            elif schwab_action.Description == "Restricted Stock Lapse":
                msg = f"{self.config.format_config.rs}{int(schwab_action.Quantity)} {schwab_action.Description}\033[0m."
            else:
                raise ValueError(
                    f"Unknown description: {schwab_action.Description}!"
                )
            print(
                f"[\033[1;37m{schwab_action.Date.strftime('%Y-%m-%d')}\033[0m]"
                f" {schwab_action.Action}:"
                f" {msg}"
            )
        return annual_income_summary

    @cached_property
    def schwab_actions(self) -> List[SchwabAction]:
        df = pd.read_csv(self.config.path)
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
        return df[::-1].apply(lambda x: SchwabAction(*x), axis=1).tolist()

    @cached_property
    def exchange_rates(self) -> Dict[datetime, ExchangeRates]:
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
        return {
            k: ExchangeRates(**v)
            for k, v in pd.concat(df_list)
            .sort_index()
            .shift()
            .to_dict(orient="index")
            .items()
        }

    @cached_property
    def remaining(self) -> float:
        curr_rate = self.exchange_rates[max(self.exchange_rates)]._1USD
        remaining = 0.0
        stocks = {}
        for share in self.schwab_buy_actions:
            if share.Symbol not in stocks:
                stocks[share.Symbol] = (
                    yf.Ticker(share.Symbol)
                    .history(period="1d")["Close"]
                    .iloc[0]
                )
            remaining += (
                stocks[share.Symbol] * curr_rate - 0.0
                if pd.isnull(share.PurchasePrice)
                else share.PurchasePrice
                * self.exchange_rates[share.Date]._1USD
            )
        return remaining
