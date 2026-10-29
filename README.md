# Business Document Intelligence Platform

A GitHub-ready RAG application for business documents. Upload PDFs, DOCX, TXT, and CSV files to ask questions with evidence, compare documents, extract structured fields, and generate evidence-backed reports.

## Features

- **Document Q&A (RAG):** retrieve relevant chunks and return grounded answers with source citations.
- **Cross-document comparison:** compare documents against a user-provided question or comparison brief.
- **Structured extraction:** extract fields from retrieved evidence into validated JSON.
- **Evidence-backed reports:** create Markdown reports with findings, supporting snippets, and source references.
- **Local-first retrieval:** TF-IDF retrieval works without paid APIs.
- **Optional LLM generation:** use OpenAI for stronger answers/extraction/report writing. Without an API key, the app provides evidence-first extractive responses.
- **Source tracking:** every chunk retains filename, page/row where available, and chunk ID.
- **Evaluation utilities:** inspect retrieval results and run a small retrieval evaluation script.
- **Privacy-conscious defaults:** files are processed locally; OpenAI calls are only made when you configure an API key and trigger a generation action.

## Quick start

Requires Python 3.10–3.12 recommended.

```bash
git clone https://github.com/YOUR_USERNAME/business-document-intelligence-platform.git
cd business-document-intelligence-platform

python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux

streamlit run app.py
```

Open the local URL shown by Streamlit. You can use the app without an OpenAI key. For LLM-powered synthesis, add `OPENAI_API_KEY` to `.env`.

## Supported file types

- PDF (`.pdf`)
- Word (`.docx`)
- Plain text (`.txt`, `.md`)
- CSV (`.csv`)

Scanned/image-only PDFs need OCR before ingestion; OCR is not included in this starter version.

## How it works

1. **Ingest:** parse uploaded documents and preserve source metadata.
2. **Chunk:** split text into overlapping passages.
3. **Index:** build a TF-IDF index over the passages.
4. **Retrieve:** rank passages for each question.
5. **Generate:** optionally send only retrieved passages to an LLM with instructions to avoid unsupported claims.
6. **Cite:** show source filename and page/row metadata alongside supporting snippets.

TF-IDF retrieval is intentionally used as a dependable, zero-API baseline. For a production deployment, swap in a dense embedding model and vector database, then evaluate both retrieval approaches on a domain-specific test set.

## Project structure

```text
business-document-intelligence-platform/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── LICENSE
├── README.md
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── ingestion.py
│   ├── chunking.py
│   ├── retrieval.py
│   ├── llm.py
│   ├── workflows.py
│   └── evaluation.py
├── tests/
│   ├── test_chunking.py
│   └── test_retrieval.py
├── scripts/
│   └── evaluate_retrieval.py
└── sample_data/
    ├── acme_company_overview.txt
    ├── acme_refund_policy.txt
    └── acme_q1_summary.txt
```

## Main workflows

### 1. Document Q&A
Ask a question and receive an answer based on the highest-ranked document passages. When OpenAI is configured, the answer is synthesized from retrieved context. Otherwise, the app returns the evidence snippets directly.

### 2. Cross-document comparison
Choose a comparison question such as *"Compare renewal terms, fees, and termination rights across these agreements."* The system retrieves evidence across all indexed documents and creates a side-by-side evidence summary.

### 3. Structured data extraction
Provide a list of fields, for example:

```text
Company name
Contract start date
Contract end date
Annual fee
Auto-renewal
Termination notice period
```

The system returns JSON containing each requested field, an evidence quote, source, and confidence status. Missing information should be returned as `Not found`, not guessed.

### 4. Evidence-backed reporting
Provide a report objective, for example *"Summarize Q1 performance, risks, and recommended follow-up questions."* The report contains an executive summary, findings, evidence, limitations, and open questions.

## Configuration

See `.env.example`.

- `OPENAI_API_KEY`: optional API key for LLM synthesis.
- `OPENAI_MODEL`: model name, default `gpt-4.1-mini`.
- `MAX_UPLOAD_MB`: per-file upload limit, default `20`.
- `CHUNK_SIZE`: approximate characters per chunk, default `1000`.
- `CHUNK_OVERLAP`: overlap between chunks, default `150`.
- `TOP_K`: number of passages retrieved by default, default `5`.

## Run tests

```bash
pytest -q
```

## Evaluate retrieval

```bash
python scripts/evaluate_retrieval.py
```

The script uses the sample data and prints whether expected source documents appear among the top retrieved results. Treat this as a smoke test, not a benchmark.

## GitHub publishing checklist

1. Create an empty GitHub repository.
2. Do **not** commit `.env`, API keys, private company files, or real customer documents.
3. Replace `YOUR_USERNAME` in this README after creating the repository.
4. Run tests and start the app locally.
5. Add screenshots/GIFs to a `docs/` folder after testing with your own sample files.
6. Add a short demo video and a sanitized evaluation report if using this for a portfolio.

## Security and limitations

- This is a portfolio MVP, not a certified enterprise records-management system.
- Do not upload confidential, regulated, or personally identifiable data unless you have approval and suitable controls.
- Uploaded files are handled in the running app process; this version does not implement persistent user accounts, access control, encryption at rest, or audit logging.
- Treat document text as untrusted input. The generation prompt instructs the model to ignore instructions embedded in documents, but prompt injection cannot be eliminated by a prompt alone.
- LLM outputs may be incorrect. Verify important claims against the displayed evidence.
- Add authentication, authorization, file scanning, rate limiting, retention controls, and stronger evaluation before deployment.
