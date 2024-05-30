import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from itertools import chain
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd
import yfinance as yf


@dataclass
class SchwabAction:
    Date: datetime = pd.NaT
    Action: str = ""
    Symbol: str = ""
    Description: str = ""
    Quantity: float = np.nan
    FeesAndCommissions: float = np.nan
    DisbursementElection: str = ""
    Amount: float = np.nan
    Type: str = ""
    Shares: float = np.nan
    SalePrice: float = np.nan
    SubscriptionDate: datetime = pd.NaT
    SubscriptionFairMarketValue: float = np.nan
    PurchaseDate: datetime = pd.NaT
    PurchasePrice: float = np.nan
    PurchaseFairMarketValue: float = np.nan
    DispositionType: str = ""
    GrantId: str = ""
    VestDate: datetime = pd.NaT
    VestFairMarketValue: float = np.nan
    GrossProceeds: float = np.nan
    AwardDate: datetime = pd.NaT
    AwardId: str = ""
    FairMarketValuePrice: float = np.nan
    SharesSoldWithheldForTaxes: float = np.nan
    NetSharesDeposited: float = np.nan
    Taxes: float = np.nan


@dataclass
class IncomeSummary:
    income: float = 0.0
    cost: float = 0.0
    gross: float = field(init=False)
    tax: float = field(init=False)
    net: float = field(init=False)

    def __post_init__(self) -> None:
        self.gross = self.income - self.cost
        self.tax = self.gross * 0.19
        self.net = self.gross - self.tax

    def __add__(self, other: "IncomeSummary") -> "IncomeSummary":
        return IncomeSummary(
            income=self.income + other.income,
            cost=self.cost + other.cost,
        )


def load_schwab_actions(path: Any) -> List[SchwabAction]:
    df = pd.read_csv(path)
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
    return list(df[::-1].apply(lambda x: SchwabAction(**x), axis=1))


def load_current_stock_values(symbols: List[str]) -> Dict[str, float]:
    return {
        symbol: yf.Ticker(symbol).history(period="1d")["Close"].iloc[0]
        for symbol in symbols
    }


def load_exchange_rates(min_year: int) -> Dict[datetime, float]:
    df_list: List[pd.DataFrame] = []
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
            .map(_try_to_float)
            .dropna(axis=1, how="all")
            .dropna(axis=0, how="all")
            .astype(float)
            .rename_axis(index="Date")
        )
        df.index = pd.to_datetime(df.index)
        df.columns = [f"_{x}" if x[0].isdigit() else x for x in df.columns]
        df_list.append(df)
    return pd.concat(df_list).sort_index().shift()["_1USD"].to_dict()


def load_summary(
    schwab_actions: List[SchwabAction],
    current_stock_values: Dict[str, float],
    exchange_rates: Dict[datetime, float],
) -> Dict[Union[int, str], IncomeSummary]:
    def _get_exchange_rate(date_: datetime) -> float:
        if date_ in exchange_rates:
            return exchange_rates[date_]
        date = sorted(filter(lambda x: x < date_, exchange_rates))[-1]
        return exchange_rates[date]

    remaining_schwab_actions: Dict[str, List[SchwabAction]] = defaultdict(list)
    summary: Dict[Union[int, str], IncomeSummary] = defaultdict(IncomeSummary)
    for schwab_action in schwab_actions:
        if schwab_action.Action == "Deposit":
            for _ in range(int(schwab_action.Quantity)):
                remaining_schwab_actions[schwab_action.Description].append(
                    schwab_action
                )
            msg = f"{schwab_action.Quantity} {schwab_action.Description} shares for {_validate_purchase_price(schwab_action) * schwab_action.Quantity:.2f} PLN."
            print(_format_msg(schwab_action, msg))
        elif schwab_action.Action == "Sale":
            sold_schwab_actions: List[SchwabAction] = []
            for _ in range(int(schwab_action.Shares)):
                sold_schwab_actions.append(
                    remaining_schwab_actions[schwab_action.Type].pop(0)
                )
                summary[schwab_action.Date.year] += IncomeSummary(
                    income=schwab_action.SalePrice
                    * _get_exchange_rate(schwab_action.Date),
                    cost=_validate_purchase_price(sold_schwab_actions[-1])
                    * _get_exchange_rate(sold_schwab_actions[-1].Date),
                )
            msg = ""
            for sold_schwab_action in sold_schwab_actions:
                msg += f"\n  -> 1 {schwab_action.Type} share for {schwab_action.SalePrice:.2f} PLN bought for {_validate_purchase_price(sold_schwab_action):.2f} PLN."
            print(_format_msg(schwab_action, msg))
        elif schwab_action.Action == "Lapse":
            msg = f"{schwab_action.Quantity} shares."
            print(_format_msg(schwab_action, msg))
        elif schwab_action.Action in [
            "Wire Transfer",
            "Tax Withholding",
            "Dividend",
        ]:
            msg = f"{schwab_action.Amount:.2f} USD."
            print(_format_msg(schwab_action, msg))
        else:
            msg = f"Unknown action! The summary may not be adequate."
            msg = _format_msg(schwab_action, msg)
            print(msg)
            print(msg, file=sys.stderr)
    summary["remaining"] = IncomeSummary()
    for remaining_schwab_action in chain(*remaining_schwab_actions.values()):
        summary["remaining"] += IncomeSummary(
            income=current_stock_values[remaining_schwab_action.Symbol]
            * next(reversed(exchange_rates.values())),
            cost=_validate_purchase_price(remaining_schwab_action)
            * _get_exchange_rate(remaining_schwab_action.Date),
        )
    return summary


def format_summary(
    summary: Dict[Union[int, str], IncomeSummary],
    employment_date: Optional[datetime] = None,
) -> str:
    df = pd.DataFrame({k: v.__dict__ for k, v in summary.items()})
    df = df.assign(total=df.sum(axis=1))
    if employment_date is not None:
        months = (datetime.now() - employment_date).days / 30.4375
        df["total/month"] = df["total"] / months
    return (
        df.style.format("{:,.2f}")
        .set_table_styles(
            [{"selector": "th, td", "props": [("text-align", "right")]}],
            overwrite=False,
        )
        .to_html()
    )


def _try_to_float(x: Any) -> Optional[float]:
    try:
        assert "," in x
        return float(x.replace(",", "."))
    except (AttributeError, ValueError, AssertionError, TypeError):
        return None


def _validate_purchase_price(schwab_action: SchwabAction) -> float:
    if pd.notnull(schwab_action.PurchasePrice):
        return schwab_action.PurchasePrice
    return 0.0


def _format_msg(schwab_action: SchwabAction, msg: str) -> str:
    return f"[{schwab_action.Date.strftime('%Y-%m-%d')}] {schwab_action.Action} ({schwab_action.Description}): {msg}"
