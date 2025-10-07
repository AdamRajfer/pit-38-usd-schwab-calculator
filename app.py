from datetime import date
from typing import Type

import streamlit as st

from polish_pit_calculator.coinbase import CoinbaseTaxReporter
from polish_pit_calculator.config import TaxRecord, TaxReport, TaxReporter
from polish_pit_calculator.ib import IBTradeCashTaxReporter
from polish_pit_calculator.raw import RawTaxReporter
from polish_pit_calculator.revolut import RevolutInterestTaxReporter
from polish_pit_calculator.schwab import SchwabEmployeeSponsoredTaxReporter


class ManualTaxReporter(TaxReporter):
    def generate(self) -> TaxReport:
        tax_data = self.args[0].copy()
        year = tax_data.pop("year")
        tax_record = TaxRecord(**tax_data)
        tax_report = TaxReport()
        tax_report[year] = tax_record
        return tax_report


class App:
    _PLACEHOLDER = "— Select Tax Reporter —"
    _YEAR_PLACEHOLDER = "— Select Year —"
    _NAME_TO_CLS: dict[str, Type[TaxReporter]] = {
        "Charles Schwab (Employee Sponsored)": SchwabEmployeeSponsoredTaxReporter,
        "Interactive Brokers (Trade Cash)": IBTradeCashTaxReporter,
        "Coinbase (Crypto)": CoinbaseTaxReporter,
        "Revolut (Interest)": RevolutInterestTaxReporter,
        "Raw (Custom CSV)": RawTaxReporter,
        "Manual Entry": ManualTaxReporter,
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
        if name == "Manual Entry":
            c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
            with c1:
                year = st.selectbox(
                    "Tax Year",
                    options=[
                        App._YEAR_PLACEHOLDER,
                        *range(date.today().year, 2019, -1),
                    ],
                    index=0,
                )
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
            if year != App._YEAR_PLACEHOLDER and st.button("Submit"):
                manual_data = {
                    "year": int(year),
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
                st.session_state.entries.append(
                    {"name": name, "data": [manual_data]}
                )
                st.rerun()
        else:
            disabled = name == App._PLACEHOLDER
            if not disabled:
                st.file_uploader(
                    "Reports (min. 1)",
                    key=files_key,
                    accept_multiple_files=True,
                )
            files = st.session_state.get(files_key, [])
            disabled = name == App._PLACEHOLDER or not files
            if not disabled and st.button("Submit"):
                st.session_state.entries.append({"name": name, "data": files})
                st.rerun()

        if st.session_state.entries:
            st.markdown("---")
            for i, entry in enumerate(st.session_state.entries):
                dg1, dg2, dg3 = st.columns([0.4, 0.5, 0.1])
                with dg1:
                    st.markdown(f"**#{i + 1}** — {entry['name']}")
                with dg2:
                    if entry["name"] == "Manual Entry":
                        manual_data = entry["data"][0]
                        st.markdown(f"**Year:** {manual_data['year']}")
                    else:
                        st.markdown(
                            "<br>".join(f"`{f.name}`" for f in entry["data"]),
                            unsafe_allow_html=True,
                        )
                with dg3:
                    if st.button("Delete", key=i):
                        st.session_state.entries.pop(i)
                        st.rerun()

        if st.session_state.entries or st.session_state.table:
            st.markdown("---")

        if (st.session_state.entries or st.session_state.table) and st.button(
            "Restart and Clear All"
        ):
            st.session_state.entries.clear()
            st.session_state.table = None
            st.rerun()

        if st.session_state.entries and st.button("Summarize"):
            tax_report = TaxReport()
            for entry in st.session_state.entries:
                tax_reporter_cls = App._NAME_TO_CLS[entry["name"]]
                if entry["name"] != "Manual Entry":
                    for f in entry["data"]:
                        f.seek(0)
                tax_reporter = tax_reporter_cls(*entry["data"])
                tax_report += tax_reporter.generate()
            df = tax_report.to_dataframe()
            rendered_df = df.style.format("{:,.2f}")
            st.session_state.table = rendered_df

        if st.session_state.table:
            st.markdown("---")
            st.table(st.session_state.table)

        return self


App().run()
