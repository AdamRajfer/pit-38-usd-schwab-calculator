from dataclasses import dataclass
from datetime import date
from enum import Enum, auto
from typing import Any, Type, cast

import streamlit as st

from polish_pit_calculator.coinbase import CoinbaseTaxReporter
from polish_pit_calculator.config import TaxRecord, TaxReport, TaxReporter
from polish_pit_calculator.ib import IBTradeCashTaxReporter
from polish_pit_calculator.raw import RawTaxReporter
from polish_pit_calculator.revolut import RevolutInterestTaxReporter
from polish_pit_calculator.schwab import SchwabEmployeeSponsoredTaxReporter


class TaxReporterType(Enum):
    FILES = auto()
    MANUAL = auto()
    PLACEHOLDER = auto()


class TaxReporterEnum(Enum):
    SELECT_TAX_REPORTER = "— Select Tax Reporter —"
    SCHWAB_EMPLOYEE_SPONSORED = "Charles Schwab (Employee Sponsored)"
    IB_TRADE_CASH = "Interactive Brokers (Trade Cash)"
    COINBASE_CRYPTO = "Coinbase (Crypto)"
    REVOLUT_INTEREST = "Revolut (Interest)"
    RAW_CUSTOM_CSV = "Raw (Custom CSV)"
    MANUAL_ENTRY = "Manual Entry"

    def to_type(self) -> TaxReporterType:
        match self:
            case TaxReporterEnum.SELECT_TAX_REPORTER:
                return TaxReporterType.PLACEHOLDER
            case TaxReporterEnum.SCHWAB_EMPLOYEE_SPONSORED:
                return TaxReporterType.FILES
            case TaxReporterEnum.IB_TRADE_CASH:
                return TaxReporterType.FILES
            case TaxReporterEnum.COINBASE_CRYPTO:
                return TaxReporterType.FILES
            case TaxReporterEnum.REVOLUT_INTEREST:
                return TaxReporterType.FILES
            case TaxReporterEnum.RAW_CUSTOM_CSV:
                return TaxReporterType.FILES
            case TaxReporterEnum.MANUAL_ENTRY:
                return TaxReporterType.MANUAL
            case _ as unknown:
                raise ValueError(f"Unknown TaxReporterEnum: {unknown}")

    def to_cls(self) -> Type[TaxReporter]:
        match self:
            case TaxReporterEnum.SELECT_TAX_REPORTER:
                raise ValueError(
                    "Cannot get TaxReporter class for PLACEHOLDER"
                )
            case TaxReporterEnum.SCHWAB_EMPLOYEE_SPONSORED:
                return SchwabEmployeeSponsoredTaxReporter
            case TaxReporterEnum.IB_TRADE_CASH:
                return IBTradeCashTaxReporter
            case TaxReporterEnum.COINBASE_CRYPTO:
                return CoinbaseTaxReporter
            case TaxReporterEnum.REVOLUT_INTEREST:
                return RevolutInterestTaxReporter
            case TaxReporterEnum.RAW_CUSTOM_CSV:
                return RawTaxReporter
            case TaxReporterEnum.MANUAL_ENTRY:
                return ManualTaxReporter
            case _ as unknown:
                raise ValueError(f"Unknown TaxReporterEnum: {unknown}")


@dataclass
class TaxReporterEntry:
    tax_reporter_enum: TaxReporterEnum
    tax_reporter_data: Any


class ManualTaxReporter(TaxReporter):
    def generate(self) -> TaxReport:
        year = self.args[0]["year"]
        tax_data = self.args[0]["tax_data"]
        tax_record = TaxRecord(**tax_data)
        tax_report = TaxReport()
        tax_report[year] = tax_record
        return tax_report


def main() -> None:
    title = "Polish PIT Calculator"
    st.set_page_config(page_title=title, layout="centered")
    st.title(title)
    st.markdown(
        """
        <style>
        .block-container {max-width: 1200px; margin: 0 auto;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.session_state.session_index = st.session_state.get("session_index", 0)
    st.session_state.entries = st.session_state.get("entries", [])
    st.session_state.table = st.session_state.get("table", None)
    if st.button("Summarize", disabled=len(st.session_state.entries) == 0):
        tax_report = TaxReport()
        for entry in st.session_state.entries:
            entry = cast(TaxReporterEntry, entry)
            tax_reporter_cls = entry.tax_reporter_enum.to_cls()
            match entry.tax_reporter_enum.to_type().value:
                case TaxReporterType.FILES.value:
                    for f in entry.tax_reporter_data:
                        f.seek(0)
                    tax_reporter = tax_reporter_cls(*entry.tax_reporter_data)
                case TaxReporterType.MANUAL.value:
                    tax_reporter = tax_reporter_cls(entry.tax_reporter_data)
                case _ as unknown:
                    raise ValueError(
                        f"Unknown TaxReporterType value: {unknown}"
                    )
            tax_report += tax_reporter.generate()
        df = tax_report.to_dataframe()
        rendered_df = df.style.format("{:,.2f}")
        st.session_state.table = rendered_df
    if st.button(
        "Restart and Clear All",
        disabled=len(st.session_state.entries) == 0
        and st.session_state.table is None,
    ):
        st.session_state.entries.clear()
        st.session_state.table = None
        st.session_state.session_index += 1
        st.rerun()
    if st.session_state.entries:
        st.markdown("---")
        for i, entry in enumerate(st.session_state.entries):
            entry = cast(TaxReporterEntry, entry)
            dg1, dg2, dg3 = st.columns([0.4, 0.5, 0.1])
            with dg1:
                st.markdown(f"**#{i + 1}** — {entry.tax_reporter_enum.value}")
            with dg2:
                match entry.tax_reporter_enum.to_type().value:
                    case TaxReporterType.FILES.value:
                        st.markdown(
                            "<br>".join(
                                f"`{f.name}`" for f in entry.tax_reporter_data
                            ),
                            unsafe_allow_html=True,
                        )
                    case TaxReporterType.MANUAL.value:
                        st.markdown(str(entry.tax_reporter_data))
                    case _ as unknown:
                        raise ValueError(
                            f"Unknown TaxReporterType value: {unknown}"
                        )
            with dg3:
                if st.button("Delete", key=i):
                    st.session_state.entries.pop(i)
                    st.rerun()
    st.markdown("---")
    tax_reporter_enum = TaxReporterEnum(
        st.selectbox(
            "Tax Reporter",
            [x.value for x in TaxReporterEnum],
            key=f"selected_tax_reporter_{st.session_state.session_index}",
            disabled=bool(
                st.session_state.get(
                    f"selected_tax_reporter_files_{st.session_state.session_index}"
                )
                or st.session_state.get(
                    f"selected_tax_reporter_year_{st.session_state.session_index}",
                    "— Select Year —",
                )
                != "— Select Year —"
            ),
        )
    )
    match tax_reporter_enum.to_type():
        case TaxReporterType.PLACEHOLDER:
            pass
        case TaxReporterType.FILES:
            files = st.file_uploader(
                "Reports (min. 1)",
                key=f"selected_tax_reporter_files_{st.session_state.session_index}",
                accept_multiple_files=True,
            )
            if files and st.button("Submit"):
                tax_reporter_entry = TaxReporterEntry(
                    tax_reporter_enum=tax_reporter_enum,
                    tax_reporter_data=files,
                )
                st.session_state.entries.append(tax_reporter_entry)
                st.session_state.session_index += 1
                st.rerun()
        case TaxReporterType.MANUAL:
            c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
            with c1:
                current_year = date.today().year
                year = st.selectbox(
                    "Tax Year",
                    options=list(range(current_year, current_year - 5, -1)),
                )
            if year != "— Select Year —":
                c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
                with c1:
                    trade_revenue = st.number_input(
                        "Trade Revenue",
                        value=0.0,
                        min_value=0.0,
                        format="%.2f",
                    )
                with c2:
                    trade_cost = st.number_input(
                        "Trade Cost",
                        value=0.0,
                        min_value=0.0,
                        format="%.2f",
                    )
                with c3:
                    trade_loss_from_previous_years = st.number_input(
                        "Trade Loss from Previous Years",
                        value=0.0,
                        min_value=0.0,
                        format="%.2f",
                    )
                c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
                with c1:
                    crypto_revenue = st.number_input(
                        "Crypto Revenue",
                        value=0.0,
                        min_value=0.0,
                        format="%.2f",
                    )
                with c2:
                    crypto_cost = st.number_input(
                        "Crypto Cost",
                        value=0.0,
                        min_value=0.0,
                        format="%.2f",
                    )
                with c3:
                    crypto_cost_excess_from_previous_years = st.number_input(
                        "Crypto Cost Excess from Previous Years",
                        value=0.0,
                        min_value=0.0,
                        format="%.2f",
                    )
                c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
                with c1:
                    domestic_interest = st.number_input(
                        "Domestic Interest",
                        value=0.0,
                        min_value=0.0,
                        format="%.2f",
                    )
                c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
                with c1:
                    foreign_interest = st.number_input(
                        "Foreign Interest",
                        value=0.0,
                        min_value=0.0,
                        format="%.2f",
                    )
                with c2:
                    foreign_interest_withholding_tax = st.number_input(
                        "Foreign Interest Withholding Tax",
                        value=0.0,
                        min_value=0.0,
                        format="%.2f",
                    )
                c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
                with c1:
                    employment_revenue = st.number_input(
                        "Employment Revenue",
                        value=0.0,
                        min_value=0.0,
                        format="%.2f",
                    )
                with c2:
                    employment_cost = st.number_input(
                        "Employment Cost",
                        value=0.0,
                        min_value=0.0,
                        format="%.2f",
                    )
                with c3:
                    social_security_contributions = st.number_input(
                        "Social Security Contributions",
                        value=0.0,
                        min_value=0.0,
                        format="%.2f",
                    )
                with c4:
                    donations = st.number_input(
                        "Donations",
                        value=0.0,
                        min_value=0.0,
                        format="%.2f",
                    )
                if st.button("Submit"):
                    tax_data = {
                        "trade_revenue": trade_revenue,
                        "trade_cost": trade_cost,
                        "trade_loss_from_previous_years": trade_loss_from_previous_years,
                        "crypto_revenue": crypto_revenue,
                        "crypto_cost": crypto_cost,
                        "crypto_cost_excess_from_previous_years": crypto_cost_excess_from_previous_years,
                        "domestic_interest": domestic_interest,
                        "foreign_interest": foreign_interest,
                        "foreign_interest_withholding_tax": foreign_interest_withholding_tax,
                        "employment_revenue": employment_revenue,
                        "employment_cost": employment_cost,
                        "social_security_contributions": social_security_contributions,
                        "donations": donations,
                    }
                    tax_reporter_entry = TaxReporterEntry(
                        tax_reporter_enum=tax_reporter_enum,
                        tax_reporter_data={
                            "year": int(year),
                            "tax_data": tax_data,
                        },
                    )
                    st.session_state.entries.append(tax_reporter_entry)
                    st.session_state.session_index += 1
                    st.rerun()
        case _ as unknown:
            raise ValueError(f"Unknown TaxReporterType: {unknown}")
    if st.session_state.table:
        st.markdown("---")
        st.table(st.session_state.table)


if __name__ == "__main__":
    main()
