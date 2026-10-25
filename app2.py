"""♀ RepresentHer demo dashboard with synthetic data and no LLM/API calls."""

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

# Inject custom CSS for column divider border and table cell text wrapping
st.markdown(
    """
    <style>
    /* Ensure parent layout containers allow full width without hidden overflow */
    [data-testid="stHorizontalBlock"] {
        align-items: stretch !important;
    }
    /* Vertical divider between main left and right columns */
    [data-testid="column"]:nth-child(1) {
        border-right: 2px solid #f8bbd0;
        padding-right: 1.5rem;
    }
    [data-testid="column"]:nth-child(2) {
        padding-left: 1.5rem;
    }

    /* Force HTML table text wrapping and column auto-resizing */
    [data-testid="stTable"] table {
        width: 100% !important;
        table-layout: auto !important;
    }
    [data-testid="stTable"] td, 
    [data-testid="stTable"] th {
        white-space: normal !important;
        word-break: break-word !important;
        overflow-wrap: break-word !important;
        vertical-align: top !important;
        padding: 8px 12px !important;
    }

    /* --- STYLE ROW 0 (Column Headers) --- */
    [data-testid="stTable"] thead tr th {
        background-color: #f0f2f6 !important;
        font-weight: normal !important;
        color: #31333f !important;
    }

    /* --- STYLE COLUMN 0 (Metric / Field Headers) --- */
    [data-testid="stTable"] tbody tr td:first-child {
        font-weight: normal !important;
        background-color: #f0f2f6 !important;
        color: #31333f !important;
    }

    /* Top-left corner cell styling (Metric / Field) */
    [data-testid="stTable"] thead tr th:first-child {
        background-color: #f0f2f6 !important;
        color: #31333f !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.title("♀ RepresentHer")
    st.caption(
        "Intelligent PDF demographic extractor & equity auditor for women's health literature "
        "(contraception, reproductive health, clinical trials)."
    )
    st.header("Upload Papers")
    uploaded_files = st.file_uploader(
        "Upload any PDF to enable the demo.",
        type=["pdf"],
        accept_multiple_files=True,
        help="The PDF is only used to enable the demo. Its contents are not read or sent anywhere.",
    )
    run_btn = st.button(
        "Run Files",
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

# --- AUTO-POLLING SIFTER DECK FRAGMENT ---
@st.fragment(run_every=1)
def poll_hardware():
    import os
    if os.path.exists("command.txt"):
        try:
            with open("command.txt", "r") as f:
                hw_cmd = f.read().strip()
            os.remove("command.txt")

            if st.session_state.demo_matrix.empty:
                st.session_state.demo_matrix = pd.DataFrame(DEMO_ROWS)

            if hw_cmd == "ACTION_AUDIT_GAPS":
                st.toast("🔴 Sifter Deck: Red Alert — Isolating high-risk compliance gaps!")
                filtered_gap = st.session_state.demo_matrix[
                    st.session_state.demo_matrix["Sex-Disaggregated?"] == "No"
                ]
                if not filtered_gap.empty:
                    st.session_state.demo_matrix = filtered_gap
                st.rerun()

            elif hw_cmd == "ACTION_EXTRACT_MATRIX":
                st.toast("🔵 Sifter Deck: Resetting matrix view...")
                st.session_state.demo_matrix = pd.DataFrame(DEMO_ROWS)
                st.rerun()

            elif hw_cmd == "ACTION_EXPORT_SUMMARY":
                st.toast("🟢 Sifter Deck: Compliance Verified! Exporting CSV...")
                st.session_state.demo_matrix.to_csv("silosifter_matrix.csv", index=False)
                st.success("Successfully exported `silosifter_matrix.csv` via hardware deck!")
                st.rerun()
        except Exception:
            pass

# Call the polling function so it runs continuously in the background
poll_hardware()

df: pd.DataFrame = st.session_state.demo_matrix

if df.empty:
# Default landing screen matching the bottom sketch (Logo + Title)
    # Centered landing screen with non-wrapping title using flexbox and viewport units (vw)
    st.markdown(
        """
        <style>
        .landing-container {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            min-height: 70vh;
            width: 100%;
            text-align: center;
        }
        .landing-title {
            white-space: nowrap;
            font-size: clamp(2rem, 6vw, 4.5rem);
            font-weight: bold;
            color: #f75775;
            margin-bottom: 0.5rem;
        }
        </style>
        <div class="landing-container">
            <div class="landing-title">♀ RepresentHer</div>
            <p style="color: #555;">Upload PDFs in the sidebar and click <b>Run Files</b> to start screening.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    # 2-col layout: left (table) & right (equity metrics + CSV preview)
    left_col, right_col = st.columns([3, 2])

    # LEFT SECTION: Table
    with left_col:
        st.subheader("Literature Screening Matrix")

        c1, c2 = st.columns([2, 1])
        with c1:
            search = st.text_input(
                "Search title / intervention / notes", 
                value="",
                placeholder="Search file"
                )
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

        # Transpose so original column labels become Column 0 data
        transposed_df = filtered.astype(str).T.reset_index()
        transposed_df.columns = ["Metric / Field"] + [f"Paper {i+1}" for i in range(len(filtered))]

        # Render as st.table to allow true multi-line CSS text wrapping without scrollbars
        st.table(transposed_df)

        st.caption(f"Showing {len(filtered)} of {len(df)} synthetic demo samples.")

    # RIGHT SECTION: Metrics & Download Preview
    with right_col:
        # Top-right panel: Equity Metrics
        st.subheader("Equity Metrics")
        st.caption("// how we are scoring equity")
        """if not filtered.empty and "Equity Score" in filtered.columns:
            avg_score = filtered["Equity Score"].mean()
            st.metric("Average Equity Score", f"{avg_score:.1f}")
        """
        st.divider()

        # Bottom-right panel: Preview, CSV & Download button
        st.subheader("CSV File Preview")
        if not filtered.empty:
            preview_subset = filtered.head(5)
            # Transpose so original columns become Column 0 rows
            preview_transposed = preview_subset.astype(str).T.reset_index()
            preview_transposed.columns = ["Metric / Field"] + [
                f"Paper {i+1}" for i in range(len(preview_subset))
            ]
            st.dataframe(
                preview_transposed,
                use_container_width=True,
                hide_index=True,
                height=180,
            )
        csv_bytes = filtered.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download CSV File",
            data=csv_bytes,
            file_name="silosifter_matrix.csv",
            mime="text/csv",
            use_container_width=True,
        )