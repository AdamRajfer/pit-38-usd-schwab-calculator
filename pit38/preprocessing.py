from collections import defaultdict
from datetime import datetime
from typing import Any, List, Optional

import pandas as pd

from pit38.stock import EXCHANGE_RATES, SchwabAction


class SchwabActionsFromFile(list[SchwabAction]):
    def __init__(self, path: str) -> None:
        super().__init__()
        self.path = path

    def load(self) -> "SchwabActionsFromFile":
        df = pd.read_csv(self.path)
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
        super().__init__(df[::-1].apply(lambda x: SchwabAction(**x), axis=1))
        return self

    def exchange(self) -> "SchwabActionsFromFile":
        self._set_exchange_rates()
        for action in self:
            action.exchange()
        return self

    def _set_exchange_rates(self) -> None:
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
                .map(self._try_to_float)
                .dropna(axis=1, how="all")
                .dropna(axis=0, how="all")
                .astype(float)
                .rename_axis(index="Date")
            )
            df.index = pd.to_datetime(df.index)
            df.columns = [f"_{x}" if x[0].isdigit() else x for x in df.columns]
            df_list.append(df)
        EXCHANGE_RATES.update(
            pd.concat(df_list).sort_index().shift()["_1USD"].to_dict()
        )

    def _try_to_float(self, x: Any) -> Optional[float]:
        try:
            assert "," in x
            return float(x.replace(",", "."))
        except (AttributeError, ValueError, AssertionError, TypeError):
            return None
