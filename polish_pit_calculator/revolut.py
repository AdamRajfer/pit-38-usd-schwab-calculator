from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from polish_pit_calculator.config import TaxRecord, TaxReport, TaxReporter


@dataclass(frozen=True)
class RevolutInterestTaxReporter(TaxReporter):
    report_paths: list[Path]

    def generate(self) -> TaxReport:
        df = self._load_report()
        tax_report = TaxReport()
        for year, df_year in df.groupby("Year"):
            tax_report[year] = TaxRecord(
                domestic_interest=df_year["Money in"].sum()
            )
        return tax_report

    def _load_report(self) -> pd.DataFrame:
        reports = []
        for path in self.report_paths:
            report = pd.read_csv(path)
            reports.append(report)
        df = pd.concat(reports, ignore_index=True)
        df = df[df["Description"].str.startswith("Gross interest")]
        df["Completed Date"] = pd.to_datetime(
            df["Completed Date"], dayfirst=True
        )
        df = df.sort_values(by="Completed Date", ignore_index=True)
        df["Year"] = df["Completed Date"].dt.year
        df["Money in"] = (
            df["Money in"]
            .str.replace(",", "", regex=False)
            .str.extract(r"([+-]?\d+(?:\.\d*)?)")
            .astype(float)
        )
        return df
