from typing import Type

import streamlit as st

from polish_pit_calculator.coinbase import CoinbaseTaxReporter
from polish_pit_calculator.config import TaxReport, TaxReporter
from polish_pit_calculator.ib import IBTradeCashTaxReporter
from polish_pit_calculator.raw import RawTaxReporter
from polish_pit_calculator.revolut import RevolutInterestTaxReporter
from polish_pit_calculator.schwab import SchwabEmployeeSponsoredTaxReporter


class App:
    _PLACEHOLDER = "— Select Tax Reporter —"
    _NAME_TO_CLS: dict[str, Type[TaxReporter]] = {
        "Charles Schwab (Employee Sponsored)": SchwabEmployeeSponsoredTaxReporter,
        "Interactive Brokers (Trade Cash)": IBTradeCashTaxReporter,
        "Coinbase (Crypto)": CoinbaseTaxReporter,
        "Revolut (Interest)": RevolutInterestTaxReporter,
        "Raw (Custom CSV)": RawTaxReporter,
    }

    def run(self) -> "App":
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

        st.session_state.entries = st.session_state.get("entries", [])
        st.session_state.table = st.session_state.get("table", None)

        if st.session_state.entries or st.session_state.table is not None:
            if st.button("Restart and Clear All"):
                st.session_state.entries.clear()
                st.session_state.table = None
                st.rerun()

        if st.session_state.entries:
            st.markdown("---")
            for i, entry in enumerate(st.session_state.entries):
                dg1, dg2, dg3 = st.columns([0.4, 0.5, 0.1])
                with dg1:
                    st.markdown(f"**#{i + 1}** — {entry['name']}")
                with dg2:
                    st.markdown(
                        "<br>".join(f"`{f.name}`" for f in entry["files"]),
                        unsafe_allow_html=True,
                    )
                with dg3:
                    if st.button("Delete", key=i):
                        st.session_state.entries.pop(i)
                        st.rerun()

        st.markdown("---")
        name_key = f"name_{len(st.session_state.entries)}"
        name = st.session_state.get(name_key, App._PLACEHOLDER)
        files_key = f"files_{len(st.session_state.entries)}"
        files = st.session_state.get(files_key, [])
        disabled = bool(files)
        st.selectbox(
            "Tax Reporter",
            [App._PLACEHOLDER, *App._NAME_TO_CLS],
            key=name_key,
            disabled=disabled,
        )
        name = st.session_state.get(name_key, App._PLACEHOLDER)
        disabled = name == App._PLACEHOLDER
        st.file_uploader(
            "Reports (min. 1)",
            key=files_key,
            accept_multiple_files=True,
            disabled=disabled,
        )
        files = st.session_state.get(files_key, [])
        disabled = name == App._PLACEHOLDER or not files
        if st.button("Submit", disabled=disabled):
            st.session_state.entries.append({"name": name, "files": files})
            st.rerun()

        st.markdown("---")
        if st.button("Summarize"):
            tax_report = TaxReport()
            for entry in st.session_state.entries:
                tax_reporter_cls = App._NAME_TO_CLS[entry["name"]]
                for f in entry["files"]:
                    f.seek(0)
                tax_reporter = tax_reporter_cls(*entry["files"])
                tax_report += tax_reporter.generate()
            df = tax_report.to_dataframe()
            rendered_df = df.style.format("{:,.2f}")
            st.session_state.table = rendered_df

        if st.session_state.table:
            st.table(st.session_state.table)

        return self


App().run()
