from argparse import ArgumentParser
from collections import defaultdict
from pathlib import Path

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


def main():
    parser = ArgumentParser()
    parser.add_argument("path", type=Path)
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
    bought = []
    total_tax = 0.0
    for i, row in df[::-1].iterrows():
        if row["Description"] == "ESPP":
            assert pd.notnull(
                row["USD-PLN"]
            ), f"Provide the exchange rate for {row['Date']}!"
            for _ in range(row["Quantity"]):
                bought.append(row)
            bought_pln = (
                row["Purchase Price"] * row["USD-PLN"] * row["Quantity"]
            )
            print(
                f"[\033[38;5;208mESPP\033[0m] Buying {row['Quantity']} shares for {bought_pln:.2f} PLN. Remaining {len(bought)} shares."
            )
        if row["Type"] == "ESPP":
            assert pd.notnull(
                row["USD-PLN"]
            ), f"Provide the exchange rate for {row['Date']}!"
            for _ in range(row["Shares"]):
                bought_row = bought.pop(0)
                sold_pln = row["Sale Price"] * row["USD-PLN"]
                bought_pln = (
                    bought_row["Purchase Price"] * bought_row["USD-PLN"]
                )
                tax = (sold_pln - bought_pln) * 0.19
                total_tax += tax
                print(
                    f"[\033[38;5;208mESPP\033[0m] Selling 1 share ({bought_row['Description']}) for {sold_pln:.2f} PLN bought for {bought_pln:.2f} PLN. Remaining {len(bought)} shares. Tax {tax:.2f} PLN. Total tax \033[1;31m{total_tax:.2f} PLN\033[0m."
                )
        if row["Description"] == "RS":
            assert pd.notnull(
                row["USD-PLN"]
            ), f"Provide the exchange rate for {row['Date']}!"
            for _ in range(row["Quantity"]):
                bought.append(row)
            print(
                f"[\033[35mRS\033[0m] Vesting {row['Quantity']} shares. Remaining {len(bought)} shares."
            )
        if row["Type"] == "RS":
            assert pd.notnull(
                row["USD-PLN"]
            ), f"Provide the exchange rate for {row['Date']}!"
            for _ in range(row["Shares"]):
                bought_row = bought.pop(0)
                sold_pln = row["Sale Price"] * row["USD-PLN"]
                tax = sold_pln * 0.19
                total_tax += tax
                print(
                    f"[\033[35mRS\033[0m] Selling 1 share ({bought_row['Description']}) for {sold_pln:.2f} PLN. Remaining {len(bought)} shares. Tax {tax:.2f} PLN. Total tax \033[1;31m{total_tax:.2f} PLN\033[0m."
                )


if __name__ == "__main__":
    main()
