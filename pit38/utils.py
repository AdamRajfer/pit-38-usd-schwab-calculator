from datetime import datetime

import pandas as pd
import requests
import yfinance as yf


def _try_to_cast_string_to_float(x) -> float | None:
    try:
        assert "," in x
        return float(x.replace(",", "."))
    except (AttributeError, ValueError, AssertionError, TypeError):
        return None


def load_current_symbol_price(symbol: str) -> float:
    return yf.Ticker(symbol).history(period="1d")["Close"].iloc[0]


def load_historical_usd_pln_exchange_rates(
    min_year: int,
) -> dict[datetime, float]:
    df_list: list[pd.DataFrame] = []
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
            .map(_try_to_cast_string_to_float)
            .dropna(axis=1, how="all")
            .dropna(axis=0, how="all")
            .astype(float)
            .rename_axis(index="Date")
        )
        df.index = pd.to_datetime(df.index)
        df.columns = [f"_{x}" if x[0].isdigit() else x for x in df.columns]
        df_list.append(df)
    return pd.concat(df_list).sort_index().shift()["_1USD"].to_dict()


def load_current_usd_pln_exchange_rate() -> float:
    return requests.get(
        "http://api.nbp.pl/api/exchangerates/rates/a/usd/?format=json"
    ).json()["rates"][0]["mid"]
