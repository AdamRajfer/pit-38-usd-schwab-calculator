from collections import defaultdict

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

with open("data/EquityAwardsCenter_Transactions_20231105144812.csv", "r") as stream:
    next(stream)
    lines = stream.read().replace("\",\n", "\"\n").split("\"\n")
lines = [x[1:].split("\",\"") for x in lines]
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
            data[curr] = pd.DataFrame([x.values for i, x in enumerate(data[curr]) if i % 2 == 1], index=[curr] * int(len(data[curr]) / 2), columns=data[curr][0].values).dropna(axis=1)
        curr = i
if curr in data:
    data[curr] = pd.DataFrame([x.values for i, x in enumerate(data[curr]) if i % 2 == 1], index=[curr] * int(len(data[curr]) / 2), columns=data[curr][0].values).dropna(axis=1)    
df_additional = pd.concat(data.values())
df = df_actions.join(df_additional)
dolar_cols = df.applymap(lambda x: "$" in x if isinstance(x, str) else False).applymap(lambda x: x or None).mean().dropna().index.tolist()
df[dolar_cols] = df[dolar_cols].applymap(lambda x: x.replace("$", "").replace(",", "").replace(".", ",") or np.nan if isinstance(x, str) else x)
columns = df.columns
df["USD-PLN"] = df["Date"].apply(lambda x: exchange_rates.get(x.strftime('%Y-%m-%d'), "")).apply(str).apply(lambda x: x.replace(".", ","))
df = df[[columns[0], "USD-PLN", *columns[1:]]]
df.set_index("Date").to_csv("data/EquityAwardsCenter_Transactions_20231105144812_processed.csv")
df
