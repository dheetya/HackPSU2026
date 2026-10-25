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

with st.sidebar:
    st.title("♀ RepresentHer")
    st.caption(
        "Intelligent PDF demographic extractor & equity auditor for women's health literature "
        "(contraception, reproductive health, clinical trials)."
    )
    st.header("Upload papers")
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
            <p style="color: #555;">Upload PDFs in the sidebar and click <b>Run RepresentHer pipeline</b> to start screening.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    # 2-col layout: left (table) & right (equity metrics + CSV preview)
    left_col, right_col = st.columns([3, 2])

    # LEFT SECTION: Table
    with left_col:
        st.subheader("Table")

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

        # RIGHT SECTION: Metrics & Download Preview
        with right_col:
            st.subheader("Equity Metrics")
            st.caption("How we score equity reporting")

            # Average score for filtered studies
            if not filtered.empty and "Equity Score" in filtered.columns:
                scores = pd.to_numeric(
                    filtered["Equity Score"],
                    errors="coerce"
                ).dropna()

                if not scores.empty:
                    avg_score = scores.mean()

                    st.metric("Average Score", f"{avg_score:.1f}/100")
                    st.progress(
                        max(0.0, min(float(avg_score) / 100, 1.0))
                    )
                    st.caption(f"Across {len(scores)} scored studies")
                else:
                    st.info("No calculated scores available.")
            else:
                st.info("No scored studies in this view.")

            st.divider()

            st.markdown(
                "We score how thoroughly studies report demographic and "
                "safety information relevant to women's health."
            )
        # Bottom-right panel: Preview, CSV & Download button
        st.subheader("Preview, CSV")
        st.dataframe(filtered.head(5), use_container_width=True, hide_index=True)

        csv_bytes = filtered.to_csv(index=False).encode("utf-8")
        st.download_button(
            "download.csv",
            data=csv_bytes,
            file_name="silosifter_matrix.csv",
            mime="text/csv",
            use_container_width=True,
        )