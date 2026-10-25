"""SiloSifter demo dashboard with synthetic data and no LLM/API calls."""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st


DEMO_ROWS = [
    {
        "Source File": "Demo sample 1",
        "Paper Title": "DEMO: Phase II contraceptive trial",
        "Intervention": "Synthetic oral contraceptive",
        "Total N": 240,
        "Female N": 240,
        "Female Cohort %": 100.0,
        "Sex-Disaggregated?": "Yes",
        "Equity Score": "Not calculated",
        "Verification": "Not run",
        "Auditor Notes": "Synthetic demo output; not derived from an uploaded PDF.",
    },
    {
        "Source File": "Demo sample 2",
        "Paper Title": "DEMO: Maternal health observational study",
        "Intervention": "Synthetic prenatal care program",
        "Total N": 1250,
        "Female N": 730,
        "Female Cohort %": 58.4,
        "Sex-Disaggregated?": "No",
        "Equity Score": "Not calculated",
        "Verification": "Not run",
        "Auditor Notes": "Synthetic demo output; sex-disaggregated results are not shown.",
    },
    {
        "Source File": "Demo sample 3",
        "Paper Title": "DEMO: Menstrual health survey",
        "Intervention": "Synthetic digital health survey",
        "Total N": 480,
        "Female N": 312,
        "Female Cohort %": 65.0,
        "Sex-Disaggregated?": "Yes",
        "Equity Score": "Not calculated",
        "Verification": "Not run",
        "Auditor Notes": "Synthetic demo output; not derived from an uploaded PDF.",
    },
]


st.set_page_config(
    page_title="RepresentHer",
    page_icon="🩸",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("SiloSifter — Demo mode")
st.caption(
    "Explore the dashboard with synthetic sample data. This demo makes no API calls "
    "and does not extract, audit, or score uploaded PDFs."
)

with st.sidebar:
    st.header("Demo")
    uploaded_files = st.file_uploader(
        "Upload any PDF to enable the demo",
        type=["pdf"],
        accept_multiple_files=True,
        help="The PDF is only used to enable the demo. Its contents are not read or sent anywhere.",
    )
    st.info("No API key is needed. Uploaded PDF contents are not processed.")
    run_btn = st.button(
        "Show synthetic demo results",
        type="primary",
        disabled=not uploaded_files,
    )

if "demo_matrix" not in st.session_state:
    st.session_state.demo_matrix = pd.DataFrame()
if "demo_compliance_log" not in st.session_state:
    st.session_state.demo_compliance_log = []

if run_btn:
    st.session_state.demo_matrix = pd.DataFrame(DEMO_ROWS)
    st.session_state.demo_compliance_log = [
        {"source_file": row["Source File"], "row": row} for row in DEMO_ROWS
    ]

df: pd.DataFrame = st.session_state.demo_matrix

if df.empty:
    st.info("Upload any PDF in the sidebar and click **Show synthetic demo results**.")
else:
    st.warning(
        "Demo data only: these example records are fictional and are not based on "
        "the uploaded PDF. Equity scoring and auditor verification are not run."
    )
    st.subheader("Literature screening matrix")

    c1, c2 = st.columns([2, 1])
    with c1:
        search = st.text_input("Search title / intervention / notes", "")
    with c2:
        sex_filter = st.selectbox(
            "Sex-disaggregated filter",
            ["All", "Yes only", "No only"],
        )

    filtered = df.copy()
    if search.strip():
        mask = filtered.apply(
            lambda row: search.lower()
            in " ".join(
                str(row.get(column, ""))
                for column in ("Paper Title", "Intervention", "Auditor Notes")
            ).lower(),
            axis=1,
        )
        filtered = filtered[mask]
    if sex_filter == "Yes only":
        filtered = filtered[filtered["Sex-Disaggregated?"] == "Yes"]
    elif sex_filter == "No only":
        filtered = filtered[filtered["Sex-Disaggregated?"] == "No"]

    st.dataframe(
        filtered,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Female Cohort %": st.column_config.NumberColumn(format="%.1f"),
        },
    )

    st.caption(f"Showing {len(filtered)} of {len(df)} synthetic demo samples.")

    col_a, col_b = st.columns(2)
    with col_a:
        st.download_button(
            "Download matrix (CSV)",
            data=filtered.to_csv(index=False).encode("utf-8"),
            file_name="silosifter_demo_matrix.csv",
            mime="text/csv",
        )
    with col_b:
        log_payload = json.dumps(st.session_state.demo_compliance_log, indent=2)
        st.download_button(
            "Download demo log (JSON)",
            data=log_payload.encode("utf-8"),
            file_name="silosifter_demo_log.json",
            mime="application/json",
        )