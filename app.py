import logging
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from functools import cached_property
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import yfinance as yf
from ansi2html import Ansi2HTMLConverter
from flask import Flask, render_template, request

app = Flask(__name__)


def try_to_float(x: Any) -> Optional[float]:
    try:
        assert "," in x
        return float(x.replace(",", "."))
    except (AttributeError, ValueError, AssertionError, TypeError):
        return None


class CaptureStdoutInHTML:
    def __enter__(self) -> "CaptureStdoutInHTML":
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self

    def __exit__(self, type: Any, value: Any, traceback: Any) -> None:
        self.content = self._stringio.getvalue()
        sys.stdout = self._stdout

    def get_html_content(self) -> str:
        return Ansi2HTMLConverter().convert(self.content, full=False)


class FormatConfig:
    espp: str = "\033[38;5;208m"
    rs: str = "\033[35m"


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
            income=self.income + other.income, cost=self.cost + other.cost
        )


@dataclass
class SchwabAction:
    Date: datetime
    Action: str
    Symbol: str
    Description: str
    Quantity: float
    FeesAndCommissions: float
    Amount: float
    Type: str
    Shares: float
    SalePrice: float
    GrantId: str
    VestDate: datetime
    VestFairMarketValue: float
    GrossProceeds: float
    AwardDate: datetime
    AwardId: str
    FairMarketValuePrice: float
    SharesSoldWithheldForTaxes: float
    NetSharesDeposited: float
    SubscriptionDate: datetime
    SubscriptionFairMarketValue: float
    PurchaseDate: datetime
    PurchasePrice: float
    PurchaseFairMarketValue: float
    DispositionType: str


@dataclass
class ExchangeRates:
    _1USD: float


class Pit38USDSchwabCalculator:
    def __init__(
        self,
        path: Path,
        employment_date: Optional[datetime] = None,
        verbose: bool = False,
    ) -> None:
        self.path = path
        self.employment_date = employment_date
        self.verbose = verbose
        self.schwab_buy_actions: List[SchwabAction] = []

    def summarize(self) -> str:
        df = pd.DataFrame(
            {k: v.__dict__ for k, v in self.annual_income_summary.items()}
        )
        df["remaining"] = pd.Series(self.remaining.__dict__)
        df["total"] = df.sum(axis=1)
        if self.employment_date is not None:
            df["total/month"] = (
                df["total"]
                / (datetime.now() - pd.to_datetime(self.employment_date)).days
                * 30.4375
            )
        df.index = [x.capitalize() for x in df.index]
        df.columns = [
            x.capitalize() if isinstance(x, str) else x for x in df.columns
        ]
        return (
            df.style.format("{:,.2f}")
            .set_table_styles(
                [{"selector": "th, td", "props": [("text-align", "right")]}],
                overwrite=False,
            )
            .to_html()
        )

    @cached_property
    def annual_income_summary(self) -> Dict[int, IncomeSummary]:
        annual_income_summary: Dict[int, IncomeSummary] = defaultdict(
            IncomeSummary
        )
        for schwab_action in self.schwab_actions:
            if schwab_action.Description in ["ESPP", "RS"]:
                msg = self._buy(schwab_action)
            elif schwab_action.Description == "Share Sale":
                msg = self._sell(schwab_action, annual_income_summary)
            elif schwab_action.Description in [
                "Cash Disbursement",
                "Debit",
                "Credit",
            ]:
                msg = f"{schwab_action.Amount:.2f} USD."
            elif schwab_action.Description == "Restricted Stock Lapse":
                msg = f"{FormatConfig.rs}{int(schwab_action.Quantity)} {schwab_action.Description}\033[0m."
            else:
                logging.warn(
                    f"Unknown schwab description: {schwab_action.Description}!"
                )
            if self.verbose:
                print(
                    f"[\033[1;37m{schwab_action.Date.strftime('%Y-%m-%d')}\033[0m]"
                    f" {schwab_action.Action}:"
                    f" {msg}"
                )
        return annual_income_summary

    @cached_property
    def schwab_actions(self) -> List[SchwabAction]:
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
        return df[::-1].apply(lambda x: SchwabAction(*x), axis=1).tolist()

    @cached_property
    def exchange_rates(self) -> Dict[datetime, ExchangeRates]:
        df_list: List[pd.DataFrame] = []
        for year in set(
            [action.Date.year for action in self.schwab_actions]
            + [datetime.now().year]
        ):
            df = (
                pd.read_csv(
                    f"https://static.nbp.pl/dane/kursy/Archiwum/archiwum_tab_a_{year}.csv",
                    delimiter=";",
                    encoding="iso-8859-2",
                    header=0,
                    skiprows=[1],
                )
                .set_index("data")
                .map(try_to_float)
                .dropna(axis=1, how="all")
                .dropna(axis=0, how="all")
                .astype(float)
                .rename_axis(index="Date")
            )
            df.index = pd.to_datetime(df.index)
            df.columns = [f"_{x}" if x[0].isdigit() else x for x in df.columns]
            df_list.append(df)
        usd = pd.concat(df_list).sort_index().shift()["_1USD"]
        return {k: ExchangeRates(**{usd.name: v}) for k, v in usd.items()}

    @cached_property
    def remaining(self) -> IncomeSummary:
        curr_rate = self.exchange_rates[max(self.exchange_rates)]._1USD
        stocks = {}
        income_summary = IncomeSummary()
        for share in self.schwab_buy_actions:
            if share.Symbol not in stocks:
                stocks[share.Symbol] = (
                    yf.Ticker(share.Symbol)
                    .history(period="1d")["Close"]
                    .iloc[0]
                )
            purchase_price = (
                0.0 if pd.isnull(share.PurchasePrice) else share.PurchasePrice
            )
            income_summary += IncomeSummary(
                income=stocks[share.Symbol] * curr_rate,
                cost=purchase_price,
            )
        return income_summary

    def _buy(self, schwab_action: SchwabAction) -> str:
        purchase_price = (
            0.0
            if pd.isnull(schwab_action.PurchasePrice)
            else schwab_action.PurchasePrice
        )
        for _ in range(int(schwab_action.Quantity)):
            self.schwab_buy_actions.append(schwab_action)
        return f"{getattr(FormatConfig, schwab_action.Description.lower())}{int(schwab_action.Quantity)} ESPP shares\033[0m for {purchase_price * self.exchange_rates[schwab_action.Date]._1USD * int(schwab_action.Quantity):.2f} PLN."

    def _sell(
        self,
        schwab_action: SchwabAction,
        annual_income_summary: Dict[int, IncomeSummary],
    ) -> str:
        msg = ""
        for _ in range(int(schwab_action.Shares)):
            schwab_buy_action = self.schwab_buy_actions.pop(0)
            purchase_price = (
                0.0
                if pd.isnull(schwab_buy_action.PurchasePrice)
                else schwab_buy_action.PurchasePrice
            )
            annual_income_summary[schwab_action.Date.year] += IncomeSummary(
                income=schwab_action.SalePrice
                * self.exchange_rates[schwab_action.Date]._1USD,
                cost=purchase_price
                * self.exchange_rates[schwab_buy_action.Date]._1USD,
            )
            msg += f"\n  -> {getattr(FormatConfig, schwab_buy_action.Description.lower())}1 {schwab_buy_action.Description} share\033[0m for {schwab_action.SalePrice * self.exchange_rates[schwab_action.Date]._1USD:.2f} PLN bought for {purchase_price * self.exchange_rates[schwab_buy_action.Date]._1USD:.2f} PLN."
        return msg


@app.route("/", methods=["GET", "POST"])
def main():
    if request.method == "POST":
        file_ = request.files["file"]
        if file_:
            with CaptureStdoutInHTML() as captured_output:
                summary = Pit38USDSchwabCalculator(
                    file_, verbose=True
                ).summarize()
            return render_template(
                "app.html",
                result=summary,
                captured_output=captured_output.get_html_content(),
            )
    return render_template("app.html", result=None, captured_output=None)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
