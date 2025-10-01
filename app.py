from typing import Type

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from polish_pit_calculator.coinbase import CoinbaseTaxReporter
from polish_pit_calculator.config import TaxReport, TaxReporter
from polish_pit_calculator.ib import IBTradeCashTaxReporter
from polish_pit_calculator.raw import RawTaxReporter
from polish_pit_calculator.revolut import RevolutInterestTaxReporter
from polish_pit_calculator.schwab import SchwabEmployeeSponsoredTaxReporter


class App:
    def __init__(self) -> None:
        st.session_state.entries = st.session_state.get("entries", [])
        st.session_state.reporter_key = st.session_state.get("reporter_key", 0)

    def clear_all_section(self) -> None:
        if st.button("Clear All", disabled=not st.session_state.entries):
            st.session_state.entries.clear()
            st.session_state.reporter_key += 1
            st.rerun()

    def entries_section(
        self, dg1: DeltaGenerator, dg2: DeltaGenerator, dg3: DeltaGenerator
    ) -> None:
        if st.session_state.entries:
            for i, entry in enumerate(st.session_state.entries):
                with dg1:
                    st.markdown(f"**#{i + 1}** — {entry['reporter_name']}")
                with dg2:
                    st.markdown(
                        ", ".join(
                            [
                                f"`{reporter_file.name}`"
                                for reporter_file in entry["reporter_files"]
                            ]
                        )
                    )
                with dg3:
                    if st.button("Delete", key=i):
                        st.session_state.entries.pop(i)
                        st.rerun()

    def add_reporter_section(
        self, dg1: DeltaGenerator, dg2: DeltaGenerator, dg3: DeltaGenerator
    ) -> None:
        reporter_files_key = f"reporter_files_{st.session_state.reporter_key}"
        reporter_files = st.session_state.get(reporter_files_key, [])
        reporter_name_key = f"reporter_name_{st.session_state.reporter_key}"
        reporter_name = st.session_state.get(
            reporter_name_key, self.reporter_name_placeholder
        )
        with dg1:
            st.selectbox(
                "Tax Reporter Type",
                [self.reporter_name_placeholder, *self.reporter_name_to_cls],
                key=reporter_name_key,
                disabled=bool(reporter_files),
            )
        with dg2:
            st.file_uploader(
                "Add reports (min. 1)",
                key=reporter_files_key,
                accept_multiple_files=True,
                disabled=reporter_name == self.reporter_name_placeholder,
            )
        reporter_files = st.session_state.get(reporter_files_key, [])
        reporter_name = st.session_state.get(
            reporter_name_key, self.reporter_name_placeholder
        )
        with dg3:
            if st.button(
                "Submit",
                disabled=reporter_name == self.reporter_name_placeholder
                or not reporter_files,
            ):
                st.session_state.entries.append(
                    {
                        "reporter_name": reporter_name,
                        "reporter_files": reporter_files,
                    }
                )
                st.session_state.reporter_key += 1
                st.rerun()

    def summary_section(self) -> None:
        if st.button("Summarize"):
            tax_report = TaxReport()
            for entry in st.session_state.entries:
                tax_reporter_cls = self.reporter_name_to_cls[
                    entry["reporter_name"]
                ]
                tax_reporter = tax_reporter_cls(*entry["reporter_files"])
                tax_report += tax_reporter.generate()
            df = tax_report.to_dataframe()
            rendered_df = df.style.format("{:,.2f}")
            st.table(rendered_df)

    def run(self) -> "App":
        st.set_page_config(
            page_title="Polish PIT Calculator",
            layout="centered",
        )
        st.markdown(
            """
            <style>
            .block-container {max-width: 1200px; margin: 0 auto;}
            .stButton>button {width: auto !important; padding: 0.45rem 0.9rem;}
            div[data-testid="stHorizontalBlock"]>div {align-self: flex-start;}
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.title("Polish PIT Calculator")
        self.clear_all_section()
        if st.session_state.entries:
            st.markdown("---")
            st.header("Tax Reporters")
        dg1, dg2, dg3 = st.columns([0.4, 0.5, 0.1])
        self.entries_section(dg1, dg2, dg3)
        st.markdown("---")
        st.header("Add Tax Reporter")
        dg1, dg2, dg3 = st.columns([0.4, 0.5, 0.1])
        self.add_reporter_section(dg1, dg2, dg3)
        st.markdown("---")
        self.summary_section()
        return self

    @property
    def reporter_name_placeholder(self) -> str:
        return "— Select Tax Reporter —"

    @property
    def reporter_name_to_cls(self) -> dict[str, Type[TaxReporter]]:
        return {
            "Charles Schwab (Employee Sponsored)": SchwabEmployeeSponsoredTaxReporter,
            "Interactive Brokers (Trade Cash)": IBTradeCashTaxReporter,
            "Coinbase (Crypto)": CoinbaseTaxReporter,
            "Revolut (Interest)": RevolutInterestTaxReporter,
            "Raw (Custom CSV)": RawTaxReporter,
        }


App().run()
