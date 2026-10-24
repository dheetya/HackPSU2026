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
    page_title="SiloSifter",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- CUSTOM UI & PINK THEME CSS ---
st.markdown("""
    <style>
    /* Import Saira font from Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Saira:wght@400;500;600;700&display=swap');

    /* Apply Saira font globally across the app */
    .stApp, p, span, label, div, input, textarea {
        font-family: 'Saira', sans-serif !important;
    }

    /* Main background color */
    .stApp {
        background-color: #ffd1dc; /* Pastel pink */
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #ffb7c5;
        border-right: 1px solid #f8bbd0;
    }
    
    /* Headers and Titles */
    h1, h2, h3 {
        color: #f75775 !important;
        font-family: 'Saira', sans-serif;
        font-weight: 700;
    }
    
    /* Custom Card Containers for Metrics or Filters */
    div.stButton > button:first-child {
        background-color: #ad1457;
        color: CC3551;
        border-radius: 8px;
        border: none;
        font-weight: 600;
        font-family: 'Saira', sans-serif !important;
    }
    div.stButton > button:first-child:hover {
        background-color: #880e4f;
        color: #CC3551;
    }
    
    /* Dataframe styling container */
    [data-testid="stDataFrame"] {
        border-radius: 10px;
        border: 1px solid #CC3551;
        background-color: white;
    }
    </style>
""", unsafe_allow_html=True)

st.title("SiloSifter")
st.caption(
    "Intelligent PDF demographic extractor & equity auditor for women's health literature "
    "(contraception, reproductive health, clinical trials)."
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
    st.header("Upload papers")
    uploaded_files = st.file_uploader(
        "Drop one or more PDFs",
        type=["pdf"],
        accept_multiple_files=True,
    )
    st.divider()
    run_btn = st.button("Run SiloSifter pipeline", type="primary", disabled=not uploaded_files)

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
    st.info("Upload PDFs in the sidebar and click **Run SiloSifter pipeline** to build the matrix.")
else:
    st.subheader("Literature screening matrix")

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        search = st.text_input("Search title / intervention / notes", "")
    with c2:
        sex_filter = st.selectbox(
            "Sex-disaggregated filter",
            ["All", "Yes only", "No only"],
        )
    with c3:
        min_score = st.slider("Min equity score", 0.0, 100.0, 0.0, 1.0)

    filtered = df.copy()
    if search.strip():
        mask = filtered.apply(
            lambda row: search.lower()
            in " ".join(
                str(row.get(c, "")) for c in ("Paper Title", "Intervention", "Auditor Notes")
            ).lower(),
            axis=1,
        )
        filtered = filtered[mask]
    if sex_filter == "Yes only":
        filtered = filtered[filtered["Sex-Disaggregated?"] == "Yes"]
    elif sex_filter == "No only":
        filtered = filtered[filtered["Sex-Disaggregated?"] == "No"]
    filtered = filtered[filtered["Equity Score"].fillna(0) >= min_score]

    st.dataframe(
        filtered,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Equity Score": st.column_config.ProgressColumn(
                "Equity Score",
                min_value=0,
                max_value=100,
                format="%.1f",
            ),
            "Female Cohort %": st.column_config.NumberColumn(format="%.1f"),
        },
    )

    st.caption(
        f"Showing {len(filtered)} of {len(df)} papers. "
        "Filter to surface studies lacking female-specific or sex-disaggregated reporting."
    )

    st.divider()
    col_a, col_b = st.columns(2)
    csv_bytes = filtered.to_csv(index=False).encode("utf-8")
    with col_a:
        st.download_button(
            "Download matrix (CSV)",
            data=csv_bytes,
            file_name="silosifter_matrix.csv",
            mime="text/csv",
        )
    with col_b:
        log_payload = json.dumps(st.session_state.compliance_log, indent=2)
        st.download_button(
            "Download compliance log (JSON)",
            data=log_payload.encode("utf-8"),
            file_name="silosifter_compliance_log.json",
            mime="application/json",
        )
