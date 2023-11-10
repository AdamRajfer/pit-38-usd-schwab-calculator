from argparse import ArgumentParser
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

exchange_rates = {
    '2023-10-03': 4.3634,
    '2023-09-21': 4.3501,
    '2023-09-20': 4.3472,
    '2023-09-05': 4.1353,
    '2023-08-31': 4.1167,
    '2023-06-14': 4.1439,
    '2023-05-30': 4.2234,
    '2023-05-22': 4.2053,
    '2023-05-08': 4.1612,
    '2023-04-04': 4.3168,
    '2023-03-17': 4.4248,
    '2023-03-01': 4.4475,
    '2023-02-28': 4.4697,
    '2022-08-31': 4.721
}

parser = ArgumentParser()
parser.add_argument("path", type=Path)
args = parser.parse_args()
with open(args.path, "r") as stream:
    next(stream)
    lines = [
        x.split(",")
        for x in stream.read().replace('"', "").replace("'", "").split("\n")
    ]
max_items = max(map(len, lines))
lines = [x + [None] * (max_items - len(x)) for x in lines]
df = pd.DataFrame(lines[1:], columns=lines[0])
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
                columns=data[curr][0].values
            ).dropna(axis=1)
        curr = i
if curr in data:
    data[curr] = pd.DataFrame(
        [x.values for i, x in enumerate(data[curr]) if i % 2 == 1],
        index=[curr] * int(len(data[curr]) / 2),
        columns=data[curr][0].values
    ).dropna(axis=1)    
df_additional = pd.concat(data.values())
df = df_actions.join(df_additional)
dolar_cols = (
    df.applymap(lambda x: ("$" in x if isinstance(x, str) else False) or None)
    .mean().dropna().index.tolist()
)
df[dolar_cols] = (
    df[dolar_cols]
    .applymap(lambda x: x.replace("$", "").replace(",", "") or None if isinstance(x, str) else x)
    .astype(float)
)
for x in df.select_dtypes(object).columns:
    if isinstance(x, str) and "Date" in x:
        df[x] = pd.to_datetime(df[x])
df["Quantity"] = df["Quantity"].apply(lambda x: x or 0).astype(int)
for x in df.select_dtypes(object).columns:
    if isinstance(x, str) and "Shares" in x:
        df[x] = df[x].fillna(0).astype(int)
df["Total Taxes"] = df["Total Taxes"].apply(lambda x: x or "NaN").astype(float)
df[df.select_dtypes(object).columns] = df.select_dtypes(object).fillna("")
df = df.rename(columns={None: "None Column", "": "Empty Column"})
df[["Empty Column", "None Column", "Grant Id"]] = df[["Empty Column", "None Column", "Grant Id"]].applymap(lambda x: x or "NaN").astype(float)
df["USD-PLN"] = df["Date"].apply(lambda x: exchange_rates.get(x.strftime('%Y-%m-%d'), None))
df[df.select_dtypes(object).columns] = df.select_dtypes(object).applymap(lambda x: x or np.nan)
df["Award ID"] = df["Award ID"].astype(float)
df.to_csv(f"{args.path}_processed.csv")
df_read = pd.read_csv(
    f"{args.path}_processed.csv",
    index_col=0,
    parse_dates=["Date", "Subscription Date", "Purchase Date", "Vest Date", "Award Date"]
)
assert (df.index == df_read.index).all()
assert (df.columns == df_read.columns).all()
assert (df.select_dtypes(object).applymap(str) == df_read.select_dtypes(object).applymap(str)).all().all()
assert (df.select_dtypes(int) == df_read.select_dtypes(int)).all().all()
assert (df.select_dtypes(float).fillna(-1) == df_read.select_dtypes(float).fillna(-1)).all().all()
assert (df.select_dtypes(np.datetime64).fillna(-1) == df_read.select_dtypes(np.datetime64).fillna(-1)).all().all()
df
