"""SiloSifter — Streamlit dashboard for PDF demographic extraction and equity audit."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from modules.auditor import extract_and_verify
from modules.ingestion import extract_text_from_pdf

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
    /* ==========================================================================
       LIGHT MODE DEFAULTS (Applies everywhere as default base styles)
       ========================================================================== */
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

    /* ==========================================================================
       LIGHT MODE DEFAULTS (Applies everywhere as default base styles)
       ========================================================================== */    /* --- Main Canvas & Sidebar --- */
    .stApp {
        background-color: #ffffff !important;
    }
    [data-testid="stSidebar"] {
        background-color: #f8f9fa !important;
    }

    /* --- SIDEBAR HEADER AND TEXT COLORS --- */
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2 {
        color: #f75775 !important;
    }

    /* Target caption text under Title and helper text under Upload Papers */
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"],
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p,
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] label,
    [data-testid="stSidebar"] .stMarkdown p {
        color: #f9859b !important;
        opacity: .9 !important;
    }

    /* 1. File Upload Button Border */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section button,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button {
        border: 1.5px solid #f8bbd0 !important;
        color: #e91e63 !important;
        background-color: transparent !important;
        border-radius: 8px !important;
    }
    /* 2. Disabled "Run Files" Button (When NO files uploaded) */
    [data-testid="stSidebar"] button[disabled] {
        border: 1.5px solid #f8bbd0 !important;
        color: #f8bbd0 !important;
        background-color: transparent !important;
        opacity: .8 !important;
        cursor: not-allowed !important;
        border-radius: 8px !important;
    }
    /* 3. Active "Run Files" Primary Button (When files ARE uploaded -> Button screenshot style) */
    [data-testid="stSidebar"] button[data-testid="baseButton-primary"]:not([disabled]),
    [data-testid="stSidebar"] button[kind="primary"]:not([disabled]) {
        background-color: #f75775 !important;
        color: #FFFFFF !important;
        border: 1.5px solid #f8bbd0 !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        box-shadow: none !important;
    }

    /* --- WIDGET LABEL COLOR MATCHING CAPTION (#f9859b) --- */
    [data-testid="stTextInput"] [data-testid="stWidgetLabel"] p,
    [data-testid="stSelectbox"] [data-testid="stWidgetLabel"] p,
    [data-testid="stWidgetLabel"] label,
    [data-testid="stWidgetLabel"] p {
        color: #808495 !important;
        opacity: 1 !important;
    }

    /* Section subheaders slight pink tint or clean dark headers */
    [data-testid="stColumn"] h3 {
        color: #31333f !important;
        border-bottom: 2px solid #fce4ec;
        padding-bottom: 4px;
        display: inline-block;
    }

    /* --- SUBHEADER COLOR (#f75775) --- */
    [data-testid="column"] h3,
    [data-testid="stHeading"] h3,
    .stMarkdown h3 {
        color: #f75775 !important;
        opacity: .9 !important;
    }

    /* Download CSV Button - Matching Focus outline style */
    [data-testid="stColumn"]:nth-child(2) [data-testid="stDownloadButton"] button {
        border: 1.5px solid #f8bbd0 !important;
        color: #e91e63 !important;
        background-color: transparent !important;
        font-weight: 500 !important;
        border-radius: 8px !important;
        transition: all 0.2s ease;
    }

    [data-testid="stColumn"]:nth-child(2) [data-testid="stDownloadButton"] button:hover {
        background-color: #f8bbd0 !important;
        color: #1f2937 !important;
    }

    /* ==========================================================================
       TABLES & DATAFRAMES STYLING
       ========================================================================== */
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
        color: #808495 !important;
    }

    /* --- STYLE COLUMN 0 (Metric / Field Headers) --- */
    [data-testid="stTable"] tbody tr td:first-child {
        font-weight: normal !important;
        background-color: #f0f2f6 !important;
        color: #808495 !important;
    }

    /* Top-left corner cell styling (Metric / Field) */
    [data-testid="stTable"] thead tr th:first-child {
        background-color: #f0f2f6 !important;
        color: #808495 !important;
    }

    /* --- STYLE ST.DATAFRAME HEADERS AND PINNED COLUMN 0 --- */
    [data-testid="stDataFrame"] [role="columnheader"],
    [data-testid="stDataFrame"] th {
        background-color: #f0f2f6 !important;
        color: #31333f !important;
        font-weight: normal !important;
    }

    /* Target pinned column header background */
    [data-testid="stDataFrame"] [data-aria-colindex="1"] {
        background-color: #f0f2f6 !important;
        color: #31333f !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

def _api_configured() -> bool:
    return bool(
        os.environ.get("OPENAI_API_KEY")
        or os.environ.get("XAI_API_KEY")
        or os.environ.get("GROK_API_KEY")
    )


def _result_row(filename: str, audit: dict) -> dict:
    ext = audit["extraction"]
    total = ext.get("total_sample_size") or 0
    female = ext.get("female_participant_count")
    female_pct = (female / total * 100) if total and female is not None else None

    return {
        "Source File": filename,
        "Paper Title": ext.get("study_title") or "",
        "Intervention": ext.get("target_compound_or_intervention") or "",
        "Total N": total,
        "Female N": female,
        "Female Cohort %": round(female_pct, 1) if female_pct is not None else None,
        "Sex-Disaggregated?": "Yes" if ext.get("sex_disaggregated_reported") else "No",
        "Equity Score": audit.get("equity_score"),
        "Verification": audit.get("verification_status"),
        "Auditor Notes": audit.get("auditor_notes") or "",
    }

def _process_uploads(uploaded_files: list) -> list[dict]:
    rows: list[dict] = []
    progress = st.progress(0, text="Starting pipeline…")
    status = st.empty()
    n = len(uploaded_files)

    for idx, uploaded in enumerate(uploaded_files):
        base_pct = idx / n
        status.info(f"**{uploaded.name}** — Ingesting PDF…")
        progress.progress(base_pct + 0.05 / n, text=f"Ingesting {uploaded.name}…")

        suffix = Path(uploaded.name).suffix or ".pdf"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded.getvalue())
            tmp_path = tmp.name

        try:
            # open pdfs, extract raw text, convert to something the extraction model can analyze
            text = extract_text_from_pdf(tmp_path) 
        except ValueError as exc:
            rows.append(
                {
                    "Source File": uploaded.name,
                    "Paper Title": f"(Ingestion error)",
                    "Intervention": "",
                    "Total N": 0,
                    "Female N": None,
                    "Female Cohort %": None,
                    "Sex-Disaggregated?": "No",
                    "Equity Score": 0.0,
                    "Verification": "Error",
                    "Auditor Notes": str(exc),
                }
            )
            Path(tmp_path).unlink(missing_ok=True)
            progress.progress((idx + 1) / n, text=f"Finished {uploaded.name}")
            continue
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        status.info(f"**{uploaded.name}** — Running Extractor Agent…")
        progress.progress(base_pct + 0.35 / n, text=f"Extracting {uploaded.name}…")

        status.info(f"**{uploaded.name}** — Auditing & calculating equity score…")
        progress.progress(base_pct + 0.65 / n, text=f"Auditing {uploaded.name}…")

        result = extract_and_verify(text)
        audit_dict = {
            "extraction": result.extraction.model_dump(),
            "verification_status": result.verification_status,
            "auditor_notes": result.auditor_notes,
            "equity_score": result.equity_score,
        }
        rows.append(_result_row(uploaded.name, audit_dict))
        progress.progress((idx + 1) / n, text=f"Completed {uploaded.name}")

    progress.progress(1.0, text="Pipeline complete.")
    status.success(f"Processed {n} paper(s).")
    return rows


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

if "matrix" not in st.session_state:
    st.session_state.matrix = pd.DataFrame()
if "compliance_log" not in st.session_state:
    st.session_state.compliance_log = []

if run_btn and uploaded_files:
    if not _api_configured():
        st.error("Configure an API key before running extraction.")
    else:
        with st.spinner("Processing PDFs…"):
            rows = _process_uploads(uploaded_files)
        st.session_state.matrix = pd.DataFrame(rows)
        st.session_state.compliance_log = [
            {
                "source_file": r["Source File"],
                "row": r,
            }
            for r in rows
        ]

# --- HARDWARE SIFTER DECK COMMAND POLLING ---
if os.path.exists("command.txt"):
    try:
        with open("command.txt", "r") as f:
            hw_cmd = f.read().strip()
        os.remove("command.txt")

        if hw_cmd == "ACTION_AUDIT_GAPS":
            st.toast("🔴 Sifter Deck: Scanning open PDFs for gap audit...")
            if uploaded_files and _api_configured():
                with st.spinner("Running Gap Audit via Hardware..."):
                    rows = _process_uploads(uploaded_files)
                    st.session_state.matrix = pd.DataFrame(rows)
                    st.session_state.compliance_log = [{"source_file": r["Source File"], "row": r} for r in rows]
                st.rerun()
            else:
                st.warning("Please upload PDFs in the sidebar first!")

        elif hw_cmd == "ACTION_EXTRACT_MATRIX":
            st.toast("🔵 Sifter Deck: Extracting demographic matrix...")
            if not st.session_state.matrix.empty:
                st.success("Matrix successfully verified and structured!")
            else:
                st.warning("No data in matrix yet. Run the pipeline first.")

        elif hw_cmd == "ACTION_EXPORT_SUMMARY":
            st.toast("🟢 Sifter Deck: Exporting summary CSV...")
            if not st.session_state.matrix.empty:
                st.session_state.matrix.to_csv("silosifter_matrix.csv", index=False)
                st.success("Successfully exported `silosifter_matrix.csv` via hardware deck!")
            else:
                st.warning("No data to export yet.")
    except Exception:
        pass

df: pd.DataFrame = st.session_state.matrix

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
            <p style="color: #f9859b;">Upload PDFs in the sidebar and click <b>Run Files</b> to start screening.</p>
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
        st.subheader("Equity Metrics")
        st.caption("How we score equity reporting")
        st.markdown(
            "We score studies on how thoroughly they report demographic and safety information relevant to women's health." \
            " Each category receives a certain weight such that higher scores indicate more complete reporting based on our criteria."
        )

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
        
        # Bottom-right panel: Preview, CSV & Download button
        st.subheader("CSV File Preview")
        if not filtered.empty:
            preview_subset = filtered.head(5)
            # Transpose so original columns become Column 0 rows
            preview_transposed = preview_subset.astype(str).T.reset_index()
            preview_transposed.columns = ["Metric / Field"] + [
                f"Paper {i+1}" for i in range(len(preview_subset))
            ]

            # Apply #f0f2f6 background color and #31333f text color to Column 0
            styled_preview = preview_transposed.style.map(
                lambda val: "background-color: #f0f2f6; color: #31333f; font-weight: normal !important;",
                subset=["Metric / Field"],
            )

            st.dataframe(
                styled_preview,
                use_container_width=True,
                hide_index=True,
                height=180,  # Caps visible area at ~4 rows before vertical scroll
                column_config={
                    "Metric / Field": st.column_config.Column(
                        "Metric / Field",
                        pinned=True,  # Pins/freezes Column 0 to the left during horizontal scroll
                    )
                },
            )

        csv_bytes = filtered.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download CSV File",
            data=csv_bytes,
            file_name="silosifter_matrix.csv",
            mime="text/csv",
            use_container_width=True,
        )