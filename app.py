import uuid
from typing import Type

import streamlit as st

from polish_pit_calculator.coinbase import CoinbaseTaxReporter
from polish_pit_calculator.config import TaxReport, TaxReporter
from polish_pit_calculator.ib import IBTradeCashTaxReporter
from polish_pit_calculator.raw import RawTaxReporter
from polish_pit_calculator.revolut import RevolutInterestTaxReporter
from polish_pit_calculator.schwab import SchwabEmployeeSponsoredTaxReporter

st.set_page_config(page_title="Polish PIT Calculator", layout="centered")
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

REPORTER_NAME_TO_CLS: dict[str, Type[TaxReporter]] = {
    "Charles Schwab (Employee Sponsored)": SchwabEmployeeSponsoredTaxReporter,
    "Interactive Brokers (Trade Cash)": IBTradeCashTaxReporter,
    "Coinbase (Crypto)": CoinbaseTaxReporter,
    "Revolut (Interest)": RevolutInterestTaxReporter,
    "Raw (Custom CSV)": RawTaxReporter,
}
PLACEHOLDER = "— Select Tax Reporter —"
OPTIONS = [PLACEHOLDER, *REPORTER_NAME_TO_CLS]

if "entries" not in st.session_state:
    st.session_state.entries = []
if "draft_kind" not in st.session_state:
    st.session_state.draft_kind = PLACEHOLDER
if "draft_key" not in st.session_state:
    st.session_state.draft_key = 0
if "reset_draft" not in st.session_state:
    st.session_state.reset_draft = False

if st.session_state.reset_draft:
    st.session_state.draft_kind = PLACEHOLDER
    st.session_state.draft_key += 1
    st.session_state.reset_draft = False

st.title("Polish PIT Calculator")

# Clear All button
if st.button(
    "Clear All", type="secondary", disabled=not st.session_state.entries
):
    st.session_state.entries = []
    st.session_state.draft_kind = PLACEHOLDER
    st.session_state.draft_key += 1
    st.session_state.reset_draft = False
    st.rerun()

if st.session_state.entries:
    st.markdown("---")
    st.header("Tax Reporters")
    for i, entry in enumerate(st.session_state.entries):
        c1, c2, c3 = st.columns([0.4, 0.5, 0.1])
        with c1:
            st.markdown(f"**#{i+1}** — {entry['kind']}")
        with c2:
            st.markdown(", ".join([f"`{f.name}`" for f in entry["files"]]))
        with c3:
            if st.button("Delete", key=entry["id"]):
                st.session_state.entries.pop(i)
                st.rerun()

st.markdown("---")

st.header("Add Tax Reporter")
col_kind, col_files, col_action = st.columns([0.4, 0.5, 0.1])

uploader_key = f"draft_uploader_{st.session_state.draft_key}"
current_files = st.session_state.get(uploader_key, [])

with col_kind:
    st.selectbox(
        "Tax Reporter Type",
        OPTIONS,
        key="draft_kind",
        disabled=bool(current_files),
    )

with col_files:
    st.file_uploader(
        "Add reports (min. 1)",
        key=uploader_key,
        accept_multiple_files=True,
        disabled=st.session_state.draft_kind == PLACEHOLDER,
    )

current_files = st.session_state.get(uploader_key, [])

with col_action:
    st.markdown('<div style="height: 28px;"></div>', unsafe_allow_html=True)
    add_clicked = st.button(
        "Submit",
        disabled=st.session_state.draft_kind not in REPORTER_NAME_TO_CLS
        or not current_files,
    )

if add_clicked:
    st.session_state.entries.append(
        {
            "id": str(uuid.uuid4()),
            "kind": st.session_state.draft_kind,
            "files": list(current_files),
        }
    )
    st.session_state.reset_draft = True
    st.rerun()

st.markdown("---")

if st.button("Summarize"):
    tax_report = TaxReport()
    for entry in st.session_state.entries:
        tax_reporter_cls = REPORTER_NAME_TO_CLS[entry["kind"]]
        tax_reporter = tax_reporter_cls(*entry["files"])
        tax_report += tax_reporter.generate()
    df = tax_report.to_dataframe()
    rendered_df = df.style.format("{:,.2f}")
    st.table(rendered_df)
