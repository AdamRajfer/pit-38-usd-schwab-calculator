from argparse import ArgumentParser
from collections import defaultdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, List, Optional, Tuple

import numpy as np
import pandas as pd


class Format(Enum):
    ESPP = "\033[38;5;208m"
    RS = "\033[35m"


def _try_to_float(x: Any) -> Optional[float]:
    try:
        assert "," in x
        return float(x.replace(",", "."))
    except (AttributeError, ValueError, AssertionError, TypeError):
        return None


def _buy_espp(row: pd.Series, bought: List[pd.Series]) -> None:
    date = row["Date"]
    exchange_rate = row["1USD"]
    assert pd.notnull(exchange_rate)
    for _ in range(row["Quantity"]):
        bought.append(row)
    bought_pln = row["Purchase Price"] * row["1USD"] * row["Quantity"]
    print(
        f"[\033[1;37m{date.strftime('%Y-%m-%d')}\033[0m]",
        f"{row['Action']} {Format.ESPP.value}{row['Quantity']}",
        "ESPP shares\033[0m",
        f"for {bought_pln:.2f} PLN.",
        f"Remaining {len(bought)} shares.",
    )


def _sell_espp(
    row: pd.Series,
    bought: List[pd.Series],
    total_gross_income: float,
    total_cost_of_earning_revenue: float,
    total_tax: float,
    year: int,
) -> Tuple[float, float, float]:
    date = row["Date"]
    exchange_rate = row["1USD"]
    assert pd.notnull(exchange_rate)
    for _ in range(row["Shares"]):
        bought_row = bought.pop(0)
        formatting = getattr(Format, bought_row["Description"]).value
        sold_pln = row["Sale Price"] * row["1USD"]
        bought_pln = bought_row["Purchase Price"] * bought_row["1USD"]
        total_gross_income += sold_pln if date.year == year else 0.0
        total_cost_of_earning_revenue += (
            bought_pln if date.year == year else 0.0
        )
        tax = (sold_pln - bought_pln) * 0.19
        total_tax += tax if date.year == year else 0.0
        print(
            f"[\033[1;37m{date.strftime('%Y-%m-%d')}\033[0m]",
            f"{row['Action']} {formatting}1 {bought_row['Description']}",
            "share\033[0m",
            f"for {sold_pln:.2f} PLN",
            f"bought for {bought_pln:.2f} PLN.",
            f"Remaining {len(bought)} shares.",
            f"Total tax for {year} \033[1;31m{total_tax:.2f} PLN\033[0m.",
        )
    return total_gross_income, total_cost_of_earning_revenue, total_tax


def _buy_rs(row: pd.Series, bought: List[pd.Series]) -> None:
    for _ in range(row["Quantity"]):
        bought.append(row)
    print(
        f"[\033[1;37m{row['Date'].strftime('%Y-%m-%d')}\033[0m]",
        f"{row['Action']} {Format.RS.value}{row['Quantity']}",
        "RS shares\033[0m.",
        f"Remaining {len(bought)} shares.",
    )


def _sell_rs(
    row: pd.Series,
    bought: List[pd.Series],
    total_gross_income: float,
    total_tax: float,
    year: int,
) -> Tuple[float, float]:
    date = row["Date"]
    exchange_rate = row["1USD"]
    assert pd.notnull(exchange_rate)
    for _ in range(row["Shares"]):
        bought_row = bought.pop(0)
        formatting = getattr(Format, bought_row["Description"]).value
        sold_pln = row["Sale Price"] * row["1USD"]
        total_gross_income += sold_pln if date.year == year else 0.0
        tax = sold_pln * 0.19
        total_tax += tax if date.year == year else 0.0
        print(
            f"[\033[1;37m{date.strftime('%Y-%m-%d')}\033[0m]",
            f"{row['Action']} {formatting}1 {bought_row['Description']}",
            "share\033[0m",
            f"for {sold_pln:.2f} PLN.",
            f"Remaining \033[1;34m{len(bought)} shares\033[0m.",
            f"Total tax for {year} \033[1;31m{total_tax:.2f} PLN\033[0m.",
        )
    return total_gross_income, total_tax


def _transferr_cash(row: pd.Series) -> None:
    print(
        f"[\033[1;37m{row['Date'].strftime('%Y-%m-%d')}\033[0m]",
        f"{row['Action']} \033[0;32m{-row['Amount']:.2f} USD\033[0m.",
        f"Included fees and commissions {-row['Fees & Commissions']:.2f} USD.",
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
    print(
        f"[\033[1;37m{row['Date'].strftime('%Y-%m-%d')}\033[0m]",
        f"{row['Action']} {row['Quantity']} {row['Description']}.",
    )


def _remaining_shares(bought: List[pd.Series]):
    print(
        f"[\033[1;37m{datetime.now().year}\033[0m]",
        f"Remaining {len(bought)} shares.",
    )


def _total_gross_income(total_gross_income: float, year: int):
    print(
        f"[\033[1;37m{year}\033[0m]",
        f"Total gross income {total_gross_income:.2f} PLN.",
    )


def _total_cost_of_earning_revenue(
    total_cost_of_earning_revenue: float, year: int
):
    print(
        f"[\033[1;37m{year}\033[0m]",
        "Total cost of earning revenue",
        f"{total_cost_of_earning_revenue:.2f} PLN.",
    )


def _total_net_income(
    total_gross_income: float, total_cost_of_earning_revenue: float, year: int
):
    print(
        f"[\033[1;37m{year}\033[0m]",
        "Total net income",
        f"{total_gross_income - total_cost_of_earning_revenue:.2f} PLN.",
    )


def _total_tax(total_tax: float, year: int):
    print(
        f"[\033[1;37m{year}\033[0m]",
        f"Total tax \033[1;31m{total_tax:.2f} PLN\033[0m.",
    )


def pit_38_usd_schwab_calculator() -> None:
    parser = ArgumentParser()
    parser.add_argument(
        "path", type=Path, help="path to the charles schwab csv file"
    )
    parser.add_argument(
        "--year",
        "-y",
        type=int,
        default=datetime.now().year - 1,
        help="taxing year (default: %(default)s)",
    )
    args = parser.parse_args()
    with open(args.path, "r") as stream:
        next(stream)
        lines = [
            x.split(",")
            for x in stream.read()
            .replace('"', "")
            .replace("'", "")
            .split("\n")
        ]
    max_items = max(map(len, lines))
    lines_validated = [x + [None] * (max_items - len(x)) for x in lines]
    df = pd.DataFrame(lines_validated[1:], columns=lines_validated[0])
    df["Date"] = pd.to_datetime(df["Date"])
    df_actions = df.dropna(subset=["Date"]).dropna(axis=1)
    curr = 0
    data = defaultdict(list)
    for i, row in df.iloc[1:].iterrows():
        if pd.isna(row["Date"]):
            data[curr].append(row)
        else:
            if curr in data:
                data[curr] = pd.DataFrame(
                    [x.values for i, x in enumerate(data[curr]) if i % 2 == 1],
                    index=[curr] * int(len(data[curr]) / 2),
                    columns=data[curr][0].values,
                ).dropna(axis=1)
            curr = i
    if curr in data:
        data[curr] = pd.DataFrame(
            [x.values for i, x in enumerate(data[curr]) if i % 2 == 1],
            index=[curr] * int(len(data[curr]) / 2),
            columns=data[curr][0].values,
        ).dropna(axis=1)
    df_additional = pd.concat(data.values())
    df = df_actions.join(df_additional)
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
    for x in df.select_dtypes(object).columns:
        if isinstance(x, str) and "Date" in x:
            df[x] = pd.to_datetime(df[x])
    df["Quantity"] = df["Quantity"].apply(lambda x: x or 0).astype(int)
    for x in df.select_dtypes(object).columns:
        if isinstance(x, str) and "Shares" in x:
            df[x] = df[x].fillna(0).astype(int)
    df["Total Taxes"] = (
        df["Total Taxes"].apply(lambda x: x or "NaN").astype(float)
    )
    df[df.select_dtypes(object).columns] = df.select_dtypes(object).fillna("")
    df = df.rename(columns={None: "None Column", "": "Empty Column"})
    df[["Empty Column", "None Column", "Grant Id"]] = (
        df[["Empty Column", "None Column", "Grant Id"]]
        .map(lambda x: x or "NaN")
        .astype(float)
    )
    exchange_rates_list = []
    for year in df["Date"].apply(lambda x: x.year).unique():
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
    df = df.merge(exchange_rates_shifted_df)
    df[df.select_dtypes(object).columns] = df.select_dtypes(object).map(
        lambda x: x or np.nan
    )
    df["Award ID"] = df["Award ID"].astype(float)
    bought: List[pd.Series] = []
    total_gross_income = 0.0
    total_cost_of_earning_revenue = 0.0
    total_tax = 0.0
    for _, row in df[::-1].iterrows():
        if row["Description"] == "ESPP":
            _buy_espp(row, bought)
        elif row["Type"] == "ESPP":
            (
                total_gross_income,
                total_cost_of_earning_revenue,
                total_tax,
            ) = _sell_espp(
                row,
                bought,
                total_gross_income,
                total_cost_of_earning_revenue,
                total_tax,
                args.year,
            )
        elif row["Description"] == "RS":
            _buy_rs(row, bought)
        elif row["Type"] == "RS":
            total_gross_income, total_tax = _sell_rs(
                row, bought, total_gross_income, total_tax, args.year
            )
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
    print(f"---\nSUMMARY\n---")
    _remaining_shares(bought)
    _total_gross_income(total_gross_income, args.year)
    _total_cost_of_earning_revenue(total_cost_of_earning_revenue, args.year)
    _total_net_income(
        total_gross_income, total_cost_of_earning_revenue, args.year
    )
    _total_tax(total_tax, args.year)


if __name__ == "__main__":
    pit_38_usd_schwab_calculator()
