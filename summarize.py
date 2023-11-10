from argparse import ArgumentParser
from collections import defaultdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd

EXCHANGE_RATES = {
    "2023-10-03": 4.3634,
    "2023-09-21": 4.3501,
    "2023-09-20": 4.3472,
    "2023-09-05": 4.1353,
    "2023-08-31": 4.1167,
    "2023-06-14": 4.1439,
    "2023-05-30": 4.2234,
    "2023-05-22": 4.2053,
    "2023-05-08": 4.1612,
    "2023-04-04": 4.3168,
    "2023-03-17": 4.4248,
    "2023-03-01": 4.4475,
    "2023-02-28": 4.4697,
    "2022-08-31": 4.721,
}


class Format(Enum):
    ESPP = "\033[38;5;208m"
    RS = "\033[35m"


def _buy_espp(row: pd.Series, bought: List[pd.Series]) -> None:
    date = row["Date"]
    exchange_rate = row["USD-PLN"]
    assert pd.notnull(exchange_rate), f"Provide the exchange rate for {date}!"
    for _ in range(row["Quantity"]):
        bought.append(row)
    bought_pln = row["Purchase Price"] * row["USD-PLN"] * row["Quantity"]
    print(
        f"[\033[1;37m{date.strftime('%Y-%m-%d')}\033[0m]",
        f"{row['Action']} {Format.ESPP.value}{row['Quantity']}",
        f"ESPP shares\033[0m",
        f"for {bought_pln:.2f} PLN.",
        f"Remaining {len(bought)} shares.",
    )


def _sell_espp(
    row: pd.Series, bought: List[pd.Series], total_tax: float, year: int
) -> float:
    date = row["Date"]
    exchange_rate = row["USD-PLN"]
    assert pd.notnull(exchange_rate), f"Provide the exchange rate for {date}!"
    for _ in range(row["Shares"]):
        bought_row = bought.pop(0)
        formatting = getattr(Format, bought_row["Description"]).value
        sold_pln = row["Sale Price"] * row["USD-PLN"]
        bought_pln = bought_row["Purchase Price"] * bought_row["USD-PLN"]
        tax = (sold_pln - bought_pln) * 0.19
        total_tax += tax if date.year == year else 0.0
        print(
            f"[\033[1;37m{date.strftime('%Y-%m-%d')}\033[0m]",
            f"{row['Action']} {formatting}1 {bought_row['Description']}",
            f"share\033[0m",
            f"for {sold_pln:.2f} PLN",
            f"bought for {bought_pln:.2f} PLN.",
            f"Remaining {len(bought)} shares.",
            f"Total tax for {year} \033[1;31m{total_tax:.2f} PLN\033[0m.",
        )
    return total_tax


def _buy_rs(row: pd.Series, bought: List[pd.Series]) -> None:
    for _ in range(row["Quantity"]):
        bought.append(row)
    print(
        f"[\033[1;37m{row['Date'].strftime('%Y-%m-%d')}\033[0m]",
        f"{row['Action']} {Format.RS.value}{row['Quantity']}",
        f"RS shares\033[0m.",
        f"Remaining {len(bought)} shares.",
    )


def _sell_rs(
    row: pd.Series, bought: List[pd.Series], total_tax: float, year: int
) -> float:
    date = row["Date"]
    exchange_rate = row["USD-PLN"]
    assert pd.notnull(exchange_rate), f"Provide the exchange rate for {date}!"
    for _ in range(row["Shares"]):
        bought_row = bought.pop(0)
        formatting = getattr(Format, bought_row["Description"]).value
        sold_pln = row["Sale Price"] * row["USD-PLN"]
        tax = sold_pln * 0.19
        total_tax += tax if date.year == year else 0.0
        print(
            f"[\033[1;37m{date.strftime('%Y-%m-%d')}\033[0m]",
            f"{row['Action']} {formatting}1 {bought_row['Description']}",
            f"share\033[0m",
            f"for {sold_pln:.2f} PLN.",
            f"Remaining \033[1;34m{len(bought)} shares\033[0m.",
            f"Total tax for {year} \033[1;31m{total_tax:.2f} PLN\033[0m.",
        )
    return total_tax


def _transferr_cash(row: pd.Series) -> None:
    print(
        f"[\033[1;37m{row['Date'].strftime('%Y-%m-%d')}\033[0m]",
        f"{row['Action']} \033[1;32m{-row['Amount']:.2f} USD\033[0m.",
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
        f"{row['Action']} \033[1;32m{row['Amount']:.2f} USD\033[0m.",
    )


def _rs_lapse(row: pd.Series) -> None:
    print(
        f"[\033[1;37m{row['Date'].strftime('%Y-%m-%d')}\033[0m]",
        f"{row['Action']} {row['Quantity']} {row['Description']}.",
    )


def _total_tax(total_tax: float, year: int):
    print(
        f"[\033[1;37m{year}\033[0m]",
        f"Total tax \033[1;31m{total_tax:.2f} PLN\033[0m.",
    )


def _remaining_shares(bought: List[pd.Series]):
    print(
        f"[\033[1;37m{datetime.now().year}\033[0m]",
        f"Remaining \033[1;34m{len(bought)} shares\033[0m.",
    )


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument(
        "path", type=Path, help="Path to the charles-schwab csv file."
    )
    parser.add_argument(
        "--year",
        type=int,
        default=datetime.now().year,
        help="Taxing year (default: %(default)s).",
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
        df.applymap(
            lambda x: ("$" in x if isinstance(x, str) else False) or None
        )
        .mean()
        .dropna()
        .index.tolist()
    )
    df[dolar_cols] = (
        df[dolar_cols]
        .applymap(
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
        .applymap(lambda x: x or "NaN")
        .astype(float)
    )
    df["USD-PLN"] = df["Date"].apply(
        lambda x: EXCHANGE_RATES.get(x.strftime("%Y-%m-%d"), None)
    )
    df[df.select_dtypes(object).columns] = df.select_dtypes(object).applymap(
        lambda x: x or np.nan
    )
    df["Award ID"] = df["Award ID"].astype(float)
    bought: List[pd.Series] = []
    total_tax = 0.0
    for _, row in df[::-1].iterrows():
        if row["Description"] == "ESPP":
            _buy_espp(row, bought)
        elif row["Type"] == "ESPP":
            total_tax = _sell_espp(row, bought, total_tax, args.year)
        elif row["Description"] == "RS":
            _buy_rs(row, bought)
        elif row["Type"] == "RS":
            total_tax = _sell_rs(row, bought, total_tax, args.year)
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
    _total_tax(total_tax, args.year)
    _remaining_shares(bought)


if __name__ == "__main__":
    main()
