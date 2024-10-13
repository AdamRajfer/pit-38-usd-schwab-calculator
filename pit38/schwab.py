import sys
from collections import defaultdict
from datetime import datetime
from itertools import chain

import pandas as pd

from pit38.config import IncomeSummary, SchwabAction
from pit38.utils import (
    load_current_symbol_price,
    load_current_usd_pln_exchange_rate,
    load_historical_usd_pln_exchange_rates,
)


def _to_zero_if_null(x) -> float:
    return 0.0 if pd.isnull(x) else x


def load_schwab_actions(path) -> list[SchwabAction]:
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
    return df[::-1].apply(lambda x: SchwabAction(**x), axis=1).tolist()


def summarize_schwab_actions(
    schwab_actions: list[SchwabAction],
) -> dict[int | str, IncomeSummary]:
    historical_usd_pln_exchange_rates = load_historical_usd_pln_exchange_rates(
        min(action.Date.year for action in schwab_actions)
    )

    def _get_usd_pln_exchange_rate(date_: datetime) -> float:
        if date_ in historical_usd_pln_exchange_rates:
            return historical_usd_pln_exchange_rates[date_]
        date_ = sorted(
            filter(lambda x: x < date_, historical_usd_pln_exchange_rates)
        )[-1]
        return historical_usd_pln_exchange_rates[date_]

    remaining_schwab_actions: dict[str, list[SchwabAction]] = defaultdict(list)
    summary: dict[int | str, IncomeSummary] = defaultdict(IncomeSummary)
    for schwab_action in schwab_actions:

        def _format_msg(msg_: str) -> str:
            return f"[{schwab_action.Date.strftime('%Y-%m-%d')}] {schwab_action.Action} ({schwab_action.Description}): {msg_}"

        if schwab_action.Action == "Deposit":
            for _ in range(int(schwab_action.Quantity)):
                remaining_schwab_actions[schwab_action.Description].append(
                    schwab_action
                )
            print(
                _format_msg(
                    f"{schwab_action.Quantity} {schwab_action.Description} shares for {_to_zero_if_null(schwab_action.PurchasePrice) * schwab_action.Quantity:.2f} USD."
                )
            )
        elif schwab_action.Action == "Sale":
            sold_schwab_actions: list[SchwabAction] = []
            for _ in range(int(schwab_action.Shares)):
                sold_schwab_actions.append(
                    remaining_schwab_actions[schwab_action.Type].pop(0)
                )
                summary[schwab_action.Date.year] += IncomeSummary(
                    income=schwab_action.SalePrice
                    * _get_usd_pln_exchange_rate(schwab_action.Date),
                    cost=_to_zero_if_null(
                        sold_schwab_actions[-1].PurchasePrice
                    )
                    * _get_usd_pln_exchange_rate(sold_schwab_actions[-1].Date),
                )
            msg = ""
            for sold_schwab_action in sold_schwab_actions:
                msg += f"\n  -> 1 {schwab_action.Type} share for {schwab_action.SalePrice:.2f} USD bought for {_to_zero_if_null(sold_schwab_action.PurchasePrice):.2f} USD."
            print(_format_msg(msg))
        elif schwab_action.Action == "Lapse":
            print(_format_msg(f"{schwab_action.Quantity} shares."))
        elif schwab_action.Action == "Dividend":
            summary[schwab_action.Date.year] += IncomeSummary(
                dividend_gross=schwab_action.Amount
                * _get_usd_pln_exchange_rate(schwab_action.Date),
            )
            print(_format_msg(f"{schwab_action.Amount:.2f} USD."))
        elif schwab_action.Action == "Tax Withholding":
            summary[schwab_action.Date.year] += IncomeSummary(
                dividend_withholding_tax=-schwab_action.Amount
                * _get_usd_pln_exchange_rate(schwab_action.Date),
            )
            print(_format_msg(f"{schwab_action.Amount:.2f} USD."))
        elif schwab_action.Action == "Wire Transfer":
            print(_format_msg(f"{schwab_action.Amount:.2f} USD."))
        else:
            msg = _format_msg(
                "Unknown action! The summary may not be adequate."
            )
            print(msg)
            print(msg, file=sys.stderr)
    summary["remaining"] = IncomeSummary()
    current_usd_pln_exchange_rate = load_current_usd_pln_exchange_rate()
    current_symbol_prices = {
        symbol: load_current_symbol_price(symbol)
        for symbol in set(
            action.Symbol
            for action in schwab_actions
            if isinstance(action.Symbol, str)
        )
    }
    for remaining_schwab_action in chain(*remaining_schwab_actions.values()):
        summary["remaining"] += IncomeSummary(
            income=current_symbol_prices[remaining_schwab_action.Symbol]
            * current_usd_pln_exchange_rate,
            cost=_to_zero_if_null(remaining_schwab_action.PurchasePrice)
            * _get_usd_pln_exchange_rate(remaining_schwab_action.Date),
        )
    return summary


def format_summary(
    summary: dict[int | str, IncomeSummary],
    employment_date: datetime | None = None,
) -> str:
    df = pd.DataFrame({k: v.__dict__ for k, v in summary.items()}).loc[
        list(IncomeSummary.__annotations__)
    ]
    df.index = df.index.str.replace("_", " ")
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
