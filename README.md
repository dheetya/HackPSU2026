# SiloSifter

SiloSifter is an MVP pipeline that ingests women's health research PDFs, extracts structured demographic and safety reporting fields with an LLM, verifies claims with an auditor agent, and scores each paper for demographic equity.

## Requirements

- Python 3.10+
- An API key for **OpenAI** or **xAI (Grok)**

## Setup

```bash
cd /path/to/HackPSU2026
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### API keys

**OpenAI (default when only `OPENAI_API_KEY` is set):**

```bash
export OPENAI_API_KEY="sk-..."
# optional
export SILOSIFTER_LLM_PROVIDER=openai
export SILOSIFTER_MODEL=gpt-4o-mini
```

**Grok / xAI:**

```bash
export XAI_API_KEY="xai-..."
export SILOSIFTER_LLM_PROVIDER=grok
export SILOSIFTER_MODEL=grok-2-latest
```

You can also use `GROK_API_KEY` instead of `XAI_API_KEY`.

## Run the dashboard

```bash
streamlit run app.py
```

Upload one or more PDFs from the sidebar, run the pipeline, then filter, search, and export the matrix as CSV or a JSON compliance log.

## Project layout

| Path | Role |
|------|------|
| `app.py` | Streamlit UI |
| `modules/ingestion.py` | PDF text extraction |
| `modules/extractor.py` | Pydantic schema + LLM extraction |
| `modules/auditor.py` | Extractor–auditor verification loop |
| `modules/equity_scorer.py` | Deterministic 0–100 equity score |
| `modules/llm_client.py` | OpenAI / Grok client with JSON mode |

## Notes

- Image-only or scanned PDFs without a text layer will fail ingestion with a clear error.
- LLM calls retry on rate limits and transient connection errors.
