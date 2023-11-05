from collections import defaultdict

import numpy as np
import pandas as pd

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
df.set_index("Date").to_csv("data/EquityAwardsCenter_Transactions_20231105144812_processed.csv")
df
