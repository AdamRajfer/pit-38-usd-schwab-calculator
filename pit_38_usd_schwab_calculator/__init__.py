from argparse import ArgumentParser
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import yfinance as yf

EXCHANGE_RATES = pd.DataFrame()


@dataclass
class Finance:
    gross: float = 0.0
    cost: float = 0.0
    net: float = field(init=False)
    tax: float = field(init=False)
    net_tax: float = field(init=False)

    def __post_init__(self) -> None:
        self.net = self.gross - self.cost
        self.tax = self.net * 0.19
        self.net_tax = self.net - self.tax

    def __add__(self, other: "Finance") -> "Finance":
        return Finance(
            gross=self.gross + other.gross, cost=self.cost + other.cost
        )


@dataclass
class State:
    employment_date: np.datetime64
    net_salary_per_month: float
    bought: List[pd.Series] = field(default_factory=list)
    finances: Dict[int, Finance] = field(
        default_factory=lambda: defaultdict(Finance)
    )

    def __str__(self) -> str:
        return self.pit_38.to_string()

    @property
    def pit_38(self) -> pd.DataFrame:
        df = pd.DataFrame(
            {
                k: {k1.replace("_", "-"): v1 for k1, v1 in v.__dict__.items()}
                for k, v in self.finances.items()
            }
        )
        total = df.sum(axis=1).to_frame("total").T
        total["remaining-tax"] = self.remaining * 0.81
        total["[(net-tax)+(remaining-tax)]/month"] = (
            (total["net-tax"] + total["remaining-tax"])
            / (datetime.now() - self.employment_date).days
            * 30
        )
        total["[(net-tax)+(remaining-tax)+(salary-tax)]/month"] = (
            total["[(net-tax)+(remaining-tax)]/month"]
            + self.net_salary_per_month
        )
        return df.join(total.T, how="right")

    @property
    def summary(self) -> pd.DataFrame:
        pit_38 = self.pit_38["total"]
        return pd.concat([pit_38, pd.Series({"remaining": self.remaining})])

    @property
    def remaining(self) -> float:
        exchange_rate = EXCHANGE_RATES.iloc[-1]["1USD"]
        remaining_usd = 0.0
        stocks = {}
        for stock in self.bought:
            if stock["Symbol"] not in stocks:
                stocks[stock["Symbol"]] = (
                    yf.Ticker(stock["Symbol"])
                    .history(period="1d")["Close"]
                    .iloc[0]
                )
            remaining_usd += stocks[stock["Symbol"]]
        return remaining_usd * exchange_rate


class Format(Enum):
    ESPP = "\033[38;5;208m"
    RS = "\033[35m"


def _try_to_float(x: Any) -> Optional[float]:
    try:
        assert "," in x
        return float(x.replace(",", "."))
    except (AttributeError, ValueError, AssertionError, TypeError):
        return None


def _buy_espp(row: pd.Series, state: State) -> None:
    date = row["Date"]
    exchange_rate = EXCHANGE_RATES.loc[row["Date"], "1USD"]
    quantity = int(row["Quantity"])
    for _ in range(quantity):
        state.bought.append(row)
    bought_pln = row["PurchasePrice"] * exchange_rate * quantity
    print(
        f"[\033[1;37m{date.strftime('%Y-%m-%d')}\033[0m]",
        f"{row['Action']} {Format.ESPP.value}{quantity}",
        "ESPP remaining\033[0m",
        f"for {bought_pln:.2f} PLN.",
        f"Remaining {len(state.bought)} shares.",
    )


def _sell_espp(row: pd.Series, state: State) -> None:
    date = row["Date"]
    exchange_rate = EXCHANGE_RATES.loc[row["Date"], "1USD"]
    remaining = int(row["Shares"])
    for _ in range(remaining):
        bought_row = state.bought.pop(0)
        formatting = getattr(Format, bought_row["Description"]).value
        pln = row["SalePrice"] * exchange_rate
        exchange_rate_bought = EXCHANGE_RATES.loc[bought_row["Date"], "1USD"]
        bought_pln = bought_row["PurchasePrice"] * exchange_rate_bought
        state.finances[date.year] += Finance(gross=pln, cost=bought_pln)
        print(
            f"[\033[1;37m{date.strftime('%Y-%m-%d')}\033[0m]",
            f"{row['Action']} {formatting}1 {bought_row['Description']}",
            "share\033[0m",
            f"for {pln:.2f} PLN",
            f"bought for {bought_pln:.2f} PLN.",
            f"Remaining {len(state.bought)} shares.",
        )


def _buy_rs(row: pd.Series, state: State) -> None:
    quantity = int(row["Quantity"])
    for _ in range(quantity):
        state.bought.append(row)
    print(
        f"[\033[1;37m{row['Date'].strftime('%Y-%m-%d')}\033[0m]",
        f"{row['Action']} {Format.RS.value}{quantity}",
        "RS remaining\033[0m.",
        f"Remaining {len(state.bought)} shares.",
    )


def _sell_rs(row: pd.Series, state: State) -> None:
    date = row["Date"]
    exchange_rate = EXCHANGE_RATES.loc[row["Date"], "1USD"]
    remaining = int(row["Shares"])
    for _ in range(remaining):
        bought_row = state.bought.pop(0)
        formatting = getattr(Format, bought_row["Description"]).value
        pln = row["SalePrice"] * exchange_rate
        state.finances[date.year] += Finance(gross=pln)
        print(
            f"[\033[1;37m{date.strftime('%Y-%m-%d')}\033[0m]",
            f"{row['Action']} {formatting}1 {bought_row['Description']}",
            "share\033[0m",
            f"for {pln:.2f} PLN.",
            f"Remaining \033[1;34m{len(state.bought)} shares\033[0m.",
        )


def _transferr_cash(row: pd.Series) -> None:
    print(
        f"[\033[1;37m{row['Date'].strftime('%Y-%m-%d')}\033[0m]",
        f"{row['Action']} \033[0;32m{-row['Amount']:.2f} USD\033[0m.",
        f"Included fees and commissions {-row['FeesAndCommissions']:.2f} USD.",
    )


def _debit(row: pd.Series) -> None:
    print(
        f"[\033[1;37m{row['Date'].strftime('%Y-%m-%d')}\033[0m]",
        f"{row['Action']} \033[1;31m{-row['Amount']:.2f} USD\033[0m.",
    )


def _credit(row: pd.Series) -> None:
    print(
        f"[\033[1;37m{row['Date'].strftime('%Y-%m-%d')}\033[0m]",
        f"{row['Action']} \033[0;32m{row['Amount']:.2f} USD\033[0m.",
    )


def _rs_lapse(row: pd.Series) -> None:
    quantity = int(row["Quantity"])
    print(
        f"[\033[1;37m{row['Date'].strftime('%Y-%m-%d')}\033[0m]",
        f"{row['Action']} {quantity} {row['Description']}.",
    )


def pit_38_usd_schwab_calculator() -> None:
    parser = ArgumentParser()
    parser.add_argument(
        "path", type=Path, help="path to the charles schwab csv file"
    )
    parser.add_argument(
        "--employment-date",
        required=True,
        type=pd.to_datetime,
        help="employment date",
    )
    parser.add_argument(
        "--net-salary-per-month",
        required=True,
        type=float,
        help="net salary per month",
    )
    args = parser.parse_args()
    df = pd.read_csv(args.path)
    df["Date"] = pd.to_datetime(df["Date"])
    df_actions = df[df["Date"].notna()].dropna(axis=1, how="all")
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
    df = df_actions.join(df_additional)
    for col in df.columns:
        if "Date" in col:
            df[col] = pd.to_datetime(df[col])
    dolar_cols = (
        df.map(lambda x: ("$" in x if isinstance(x, str) else False) or None)
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
    exchange_rates_list = []
    for year in {
        *df.select_dtypes(np.datetime64).stack().apply(lambda x: x.year),
        datetime.now().year,
    }:
        exchange_rates = (
            pd.read_csv(
                f"https://static.nbp.pl/dane/kursy/Archiwum/archiwum_tab_a_{year}.csv",
                delimiter=";",
                encoding="iso-8859-2",
                header=0,
                skiprows=[1],
            )
            .set_index("data")
            .map(_try_to_float)
            .dropna(axis=1, how="all")
            .dropna(axis=0, how="all")
            .astype(float)
            .rename_axis(index="Date")
            .reset_index()
        )
        exchange_rates["Date"] = pd.to_datetime(exchange_rates["Date"])
        exchange_rates_list.append(exchange_rates)
    exchange_rates_df = pd.concat(exchange_rates_list).sort_values(
        by="Date", ignore_index=True
    )
    exchange_rates_shifted_df = exchange_rates_df.shift()
    exchange_rates_shifted_df["Date"] = exchange_rates_df["Date"]
    global EXCHANGE_RATES
    EXCHANGE_RATES = exchange_rates_shifted_df.set_index("Date")
    state = State(
        employment_date=args.employment_date,
        net_salary_per_month=args.net_salary_per_month,
    )
    for _, row in df[::-1].iterrows():
        if row["Description"] == "ESPP":
            _buy_espp(row, state)
        elif row["Type"] == "ESPP":
            _sell_espp(row, state)
        elif row["Description"] == "RS":
            _buy_rs(row, state)
        elif row["Type"] == "RS":
            _sell_rs(row, state)
        elif row["Description"] == "Cash Disbursement":
            _transferr_cash(row)
        elif row["Description"] == "Debit":
            _debit(row)
        elif row["Description"] == "Credit":
            _credit(row)
        elif row["Description"] == "Restricted Stock Lapse":
            _rs_lapse(row)
        else:
            raise ValueError(f"Unknown description: {row['Description']}!")
    print(state)


if __name__ == "__main__":
    pit_38_usd_schwab_calculator()
