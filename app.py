from __future__ import annotations
import json
from pathlib import Path
import streamlit as st

from src.config import MAX_UPLOAD_MB, CHUNK_SIZE, CHUNK_OVERLAP, TOP_K
from src.ingestion import parse_uploaded_file
from src.chunking import build_chunks
from src.retrieval import TfidfRetriever
from src.llm import llm_available
from src.workflows import answer_question, compare_documents, extract_fields, build_report

st.set_page_config(page_title="Business Document Intelligence", page_icon="📚", layout="wide")

st.title("📚 Business Document Intelligence Platform")
st.caption("RAG-powered document Q&A · cross-document comparison · structured extraction · evidence-backed reporting")

with st.sidebar:
    st.header("Workspace")
    st.write("Upload business documents to create a temporary searchable workspace.")
    st.caption("Files stay in this running app process. Refreshing/restarting may clear the workspace.")
    st.divider()
    st.write("**Generation mode**")
    if llm_available():
        st.success("LLM enabled")
    else:
        st.info("Evidence-only mode")
        st.caption("Set OPENAI_API_KEY in `.env` to enable grounded LLM synthesis.")
    top_k = st.slider("Retrieved passages", min_value=1, max_value=12, value=TOP_K)
    st.caption(f"Chunk size: {CHUNK_SIZE} chars · overlap: {CHUNK_OVERLAP} chars")
    if st.button("Clear workspace", use_container_width=True):
        for key in ("chunks", "retriever", "uploaded_names", "raw_records"):
            st.session_state.pop(key, None)
        st.rerun()

if "chunks" not in st.session_state:
    st.session_state.chunks = []
    st.session_state.retriever = TfidfRetriever()
    st.session_state.uploaded_names = []
    st.session_state.raw_records = []

tab_upload, tab_qa, tab_compare, tab_extract, tab_report = st.tabs([
    "1 · Ingest documents", "2 · Ask questions", "3 · Compare documents",
    "4 · Extract fields", "5 · Generate report"
])

with tab_upload:
    st.subheader("Build your document workspace")
    uploads = st.file_uploader(
        "Choose files", type=["pdf", "docx", "txt", "md", "csv"],
        accept_multiple_files=True,
        help=f"Maximum {MAX_UPLOAD_MB} MB per file."
    )
    if st.button("Process selected files", type="primary", disabled=not uploads):
        existing_names = set(st.session_state.uploaded_names)
        new_records, new_names = [], []
        progress = st.progress(0)
        for i, uploaded in enumerate(uploads):
            if uploaded.size > MAX_UPLOAD_MB * 1024 * 1024:
                st.error(f"{uploaded.name} exceeds the {MAX_UPLOAD_MB} MB limit.")
                continue
            if uploaded.name in existing_names:
                st.warning(f"{uploaded.name} is already in the workspace and was skipped.")
                continue
            try:
                parsed = parse_uploaded_file(uploaded.name, uploaded.getvalue())
                new_records.extend(parsed)
                new_names.append(uploaded.name)
            except Exception as exc:
                st.error(f"Could not process {uploaded.name}: {exc}")
            progress.progress((i + 1) / len(uploads))
        if new_records:
            new_chunks = build_chunks(new_records, CHUNK_SIZE, CHUNK_OVERLAP)
            st.session_state.raw_records.extend(new_records)
            st.session_state.chunks.extend(new_chunks)
            st.session_state.uploaded_names.extend(new_names)
            retriever = TfidfRetriever()
            retriever.fit(st.session_state.chunks)
            st.session_state.retriever = retriever
            st.success(f"Indexed {len(new_names)} file(s), {len(new_records)} source records, and {len(new_chunks)} chunks.")
    if st.session_state.uploaded_names:
        st.subheader("Indexed files")
        for name in st.session_state.uploaded_names:
            st.write(f"• {name}")
        st.caption(f"{len(st.session_state.chunks)} searchable chunks in this session.")
    else:
        st.info("No documents yet. Try the included sample files in `sample_data/`.")

has_docs = bool(st.session_state.chunks)
if not has_docs:
    st.warning("Upload at least one document in the first tab to use the workflows.")

with tab_qa:
    st.subheader("Ask questions across your documents")
    question = st.text_area("Question", placeholder="What are the key renewal terms and fees?", key="qa_question")
    if st.button("Find answer", type="primary", disabled=not has_docs or not question.strip(), key="qa_button"):
        evidence = st.session_state.retriever.search(question, top_k)
        st.session_state.last_evidence = evidence
        st.markdown(answer_question(question, evidence))
        with st.expander("Retrieved evidence"):
            for i, item in enumerate(evidence, 1):
                st.markdown(f"**[S{i}] {item['source']} — {item['location']} · score {item['score']:.3f}**")
                st.write(item["text"])

with tab_compare:
    st.subheader("Compare evidence across documents")
    brief = st.text_area("What should be compared?", placeholder="Compare pricing, renewal, termination, and liability terms across all contracts.", key="compare_brief")
    if st.button("Compare documents", type="primary", disabled=not has_docs or not brief.strip(), key="compare_button"):
        evidence = st.session_state.retriever.search(brief, max(top_k, min(len(st.session_state.chunks), top_k * 2)))
        st.markdown(compare_documents(brief, evidence))
        with st.expander("Comparison evidence"):
            for i, item in enumerate(evidence, 1):
                st.markdown(f"**[S{i}] {item['source']} — {item['location']}**")
                st.write(item["text"])

with tab_extract:
    st.subheader("Extract fields into structured JSON")
    fields = st.text_area(
        "Fields to extract (one per line)",
        value="Company name\nEffective date\nContract end date\nAnnual fee\nAuto-renewal\nTermination notice period",
        key="extract_fields"
    )
    extract_query = st.text_input("Optional retrieval hint", value="contract dates fees renewal termination company name", key="extract_query")
    if st.button("Extract fields", type="primary", disabled=not has_docs, key="extract_button"):
        evidence = st.session_state.retriever.search(extract_query + "\n" + fields, top_k * 2)
        result = extract_fields(fields, evidence)
        st.json(result)
        st.download_button("Download extraction JSON", data=json.dumps(result, indent=2), file_name="extracted_fields.json", mime="application/json")

with tab_report:
    st.subheader("Generate an evidence-backed report")
    objective = st.text_area("Report objective", placeholder="Summarize Q1 performance, identify major risks, and list unanswered questions.", key="report_objective")
    report_query = st.text_input("Evidence search hint (optional)", key="report_query", placeholder="Revenue, costs, risks, milestones")
    if st.button("Generate report", type="primary", disabled=not has_docs or not objective.strip(), key="report_button"):
        query = report_query.strip() or objective
        evidence = st.session_state.retriever.search(query, top_k * 2)
        report = build_report(objective, evidence)
        st.markdown(report)
        st.download_button("Download Markdown report", data=report, file_name="evidence_backed_report.md", mime="text/markdown")
        with st.expander("Evidence included in report"):
            for i, item in enumerate(evidence, 1):
                st.markdown(f"**[S{i}] {item['source']} — {item['location']}**")
                st.write(item["text"])

st.divider()
st.caption("Portfolio MVP · Verify important claims against original sources. Do not upload confidential documents without authorization.")
