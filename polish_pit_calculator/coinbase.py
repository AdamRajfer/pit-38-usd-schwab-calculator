from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from polish_pit_calculator.config import TaxRecord, TaxReport, TaxReporter
from polish_pit_calculator.utils import fetch_exchange_rates, get_exchange_rate


@dataclass(frozen=True)
class CoinbaseTaxReporter(TaxReporter):
    report_path: Path

    def generate(self) -> TaxReport:
        df = self._load_report()
        tax_report = TaxReport()
        for year, df_year in df.groupby("Year"):
            tax_report[year] = TaxRecord(
                crypto_revenue=df_year["Income"].sum(),
                crypto_cost=df_year["Cost"].sum(),
            )
        return tax_report

    def _load_report(self) -> pd.DataFrame:
        df = pd.read_csv(
            self.report_path, skiprows=3, parse_dates=["Timestamp"]
        )
        df["Timestamp"] = df["Timestamp"].dt.date
        df["Year"] = df["Timestamp"].apply(lambda x: x.year)
        df = df[
            df["Transaction Type"].isin(
                ["Advanced Trade Buy", "Advanced Trade Sell"]
            )
        ]
        for col in ["Subtotal", "Fees and/or Spread"]:
            df[col] = df[col].str.extract(r"[^\d](.*)").astype(float)
        df[["Cost", "Income"]] = 0.0
        buy = df[df["Transaction Type"] == "Advanced Trade Buy"]
        if not buy.empty:
            buy["Cost"] += buy["Subtotal"]
            buy["Cost"] += buy["Fees and/or Spread"]
        sell = df[df["Transaction Type"] == "Advanced Trade Sell"]
        if not sell.empty:
            sell["Income"] += sell["Subtotal"]
            sell["Cost"] += sell["Fees and/or Spread"]
        df = pd.concat([buy, sell])
        exchange_rates = fetch_exchange_rates(df["Year"].min())
        exc_rate = df.apply(
            lambda x: get_exchange_rate(
                currency=x["Price Currency"],
                date_=x["Timestamp"],
                exchange_rates=exchange_rates,
            ),
            axis=1,
        )
        df["Cost"] *= exc_rate
        df["Income"] *= exc_rate
        return df
