from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
from tabulate import tabulate


@dataclass(frozen=True)
class TaxRecord:
    trade_revenue: float = 0.0
    trade_cost: float = 0.0
    trade_loss_from_previous_years: float = 0.0
    crypto_revenue: float = 0.0
    crypto_cost: float = 0.0
    crypto_cost_excess_from_previous_years: float = 0.0
    domestic_interest: float = 0.0
    foreign_interest: float = 0.0
    foreign_interest_withholding_tax: float = 0.0
    employment_revenue: float = 0.0
    employment_cost: float = 0.0
    social_security_contributions: float = 0.0
    donations: float = 0.0

    @property
    def trade_profit(self) -> float:
        amount = (
            self.trade_revenue
            - self.trade_cost
            - self.trade_loss_from_previous_years
        )
        return amount if amount > 0.0 else 0.0

    @property
    def trade_loss(self) -> float:
        amount = (
            self.trade_revenue
            - self.trade_cost
            - self.trade_loss_from_previous_years
        )
        return -amount if amount < 0.0 else 0.0

    @property
    def trade_tax(self) -> float:
        return self.trade_profit * 0.19

    @property
    def crypto_profit(self) -> float:
        amount = (
            self.crypto_revenue
            - self.crypto_cost
            - self.crypto_cost_excess_from_previous_years
        )
        return amount if amount > 0.0 else 0.0

    @property
    def crypto_cost_excess(self) -> float:
        amount = (
            self.crypto_revenue
            - self.crypto_cost
            - self.crypto_cost_excess_from_previous_years
        )
        return -amount if amount < 0.0 else 0.0

    @property
    def crypto_tax(self) -> float:
        return self.crypto_profit * 0.19

    @property
    def domestic_interest_tax(self) -> float:
        return self.domestic_interest * 0.19

    @property
    def foreign_interest_tax(self) -> float:
        return self.foreign_interest * 0.19

    @property
    def foreign_interest_remaining_tax(self) -> float:
        return max(
            self.foreign_interest_tax - self.foreign_interest_withholding_tax,
            0.0,
        )

    @property
    def employment_profit(self) -> float:
        return self.employment_revenue - self.employment_cost

    @property
    def employment_profit_deduction(self) -> float:
        return min(0.06 * self.employment_profit, self.donations)

    @property
    def total_profit(self) -> float:
        return self.employment_profit + self.trade_profit + self.crypto_profit

    @property
    def total_profit_deductions(self) -> float:
        return (
            self.employment_profit_deduction
            + self.social_security_contributions
        )

    @property
    def solidarity_tax(self) -> float:
        return (
            max(self.total_profit - self.total_profit_deductions - 1e6, 0.0)
            * 0.04
        )

    @property
    def total_tax(self) -> float:
        return (
            self.trade_tax
            + self.crypto_tax
            + self.domestic_interest_tax
            + self.foreign_interest_remaining_tax
            + self.solidarity_tax
        )

    def to_dict(self) -> dict[str, float]:
        return {
            "Trade Revenue (PIT-38/C20)": self.trade_revenue,
            "Trade Cost (PIT-38/C21)": self.trade_cost,
            "Trade Loss from Previous Years (PIT-38/D28)": self.trade_loss_from_previous_years,
            "Trade Loss (PIT-38/D28 - Next Year)": self.trade_loss,
            "Crypto Revenue (PIT-38/E34)": self.crypto_revenue,
            "Crypto Cost (PIT-38/E35)": self.crypto_cost,
            "Crypto Cost Excess from Previous Years (PIT-38/E36)": self.crypto_cost_excess_from_previous_years,
            "Crypto Cost Excess (PIT-38/E36 - Next Year)": self.crypto_cost_excess,
            "Domestic Interest Tax (PIT-38/G44)": self.domestic_interest_tax,
            "Foreign Interest Tax (PIT-38/G45)": self.foreign_interest_tax,
            "Foreign Interest Withholding Tax (PIT-38/G46)": self.foreign_interest_withholding_tax,
            "Employment Profit Deduction (PIT/O/B11 -> PIT-37/F124)": self.employment_profit_deduction,
            "Total Profit (DSF-1/C18 - If Solidarity Tax > 0.00)": self.total_profit,
            "Total Profit Deductions (DSF-1/CC19 - If Solidarity Tax > 0.00)": self.total_profit_deductions,
            "Solidarity Tax": self.solidarity_tax,
            "Total Tax": self.total_tax,
        }

    def __add__(self, other: "TaxRecord") -> "TaxRecord":
        kwargs = {
            field: getattr(self, field) + getattr(other, field)
            for field in TaxRecord.__dataclass_fields__
        }
        return TaxRecord(**kwargs)


@dataclass(frozen=True)
class TaxReport:
    year_to_tax_record: dict[int, TaxRecord] = field(default_factory=dict)

    def __add__(self, other: "TaxReport") -> "TaxReport":
        tax_report = TaxReport()
        for year in set(self.year_to_tax_record).union(
            other.year_to_tax_record
        ):
            if year not in self.year_to_tax_record:
                tax_report[year] = other[year]
            elif year not in other.year_to_tax_record:
                tax_report[year] = self[year]
            else:
                tax_report[year] = self[year] + other[year]
        return tax_report

    def __getitem__(self, year: int) -> TaxRecord:
        return self.year_to_tax_record.get(year, TaxRecord())

    def __setitem__(self, year: int, tax_record: TaxRecord) -> None:
        if year in self.year_to_tax_record:
            raise ValueError(f"Tax record for year {year} already registered.")
        self.year_to_tax_record[year] = tax_record

    def items(self) -> list[tuple[int, TaxRecord]]:
        return list(self.year_to_tax_record.items())

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame.from_dict(
            {k: v.to_dict() for k, v in self.items()},
            orient="index",
        ).T.sort_index(axis=1)

    def to_string(self) -> str:
        return tabulate(
            self.to_dataframe(),
            headers="keys",
            tablefmt="github",
            floatfmt=",.2f",
        )


@dataclass(frozen=True)
class TaxReporter(ABC):
    @abstractmethod
    def generate(self) -> TaxReport:
        pass


@dataclass(frozen=True)
class SavingsConfig:
    cash: float
    interest_rate: float


@dataclass(frozen=True)
class TaxSummaryConfig:
    tax_reporters: list[TaxReporter]
    savings: SavingsConfig


@dataclass(frozen=True)
class DashboardConfig:
    data_dir: Path
    properties: dict[str, dict[str, dict[str, str]]]
