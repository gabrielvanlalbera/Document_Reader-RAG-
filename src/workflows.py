"""Business workflows built on retrieval and optional grounded generation."""
from __future__ import annotations

import json
import re
from collections import defaultdict

from src.llm import generate


_STOP_WORDS = {
    "what", "is", "are", "the", "a", "an", "of", "in", "on", "to", "for",
    "and", "or", "does", "do", "how", "why", "who", "which", "this", "that",
    "their", "its", "it", "company", "organization", "please", "tell", "me",
    "about", "summarize", "summary", "explain", "describe", "give", "provide",
    "can", "could", "would", "should", "from", "with", "across", "based", "document",
}

_SYNONYMS = {
    "mission": {"purpose", "goal", "goals", "objective", "objectives", "aim", "aims"},
    "vision": {"future", "aspiration", "aspirations", "direction"},
    "aim": {"goal", "goals", "purpose", "objective", "objectives", "mission"},
    "objectives": {"goals", "aims", "purpose", "targets", "mission"},
    "organization": {"company", "business", "firm", "enterprise", "team"},
    "activities": {"services", "solutions", "products", "operations", "work"},
    "business": {"services", "solutions", "clients", "industries", "operations"},
    "services": {"solutions", "offer", "offers", "provide", "provides"},
    "revenue": {"sales", "income", "earnings", "financial"},
    "skills": {"proficient", "experience", "knowledge", "requirements"},
    "industry": {"industries", "sector", "sectors", "markets"},
    "client": {"clients", "customer", "customers", "enterprise"},
}


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def evidence_only_answer(question: str, evidence: list[dict]) -> str:
    """Create an extractive, cited answer when no LLM API key is configured.

    This deliberately quotes or lightly selects source sentences instead of inventing
    a summary. It is a fallback, not equivalent to LLM synthesis.
    """
    if not evidence:
        return (
            "I couldn't find relevant evidence in the indexed documents. "
            "Try different wording, check the extracted PDF text, or upload a more relevant source."
        )

    query_words = _words(question) - _STOP_WORDS
    expanded_words = set(query_words)
    for word in query_words:
        expanded_words.update(_SYNONYMS.get(word, set()))

    candidates: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for item in evidence:
        text = item.get("text", "").strip()
        if not text:
            continue
        # PDF extraction often joins lines; split conservatively at sentence boundaries.
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])", text)
        if len(sentences) == 1:
            # Some PDFs omit spaces after punctuation; also split on common bullet separators.
            sentences = re.split(r"\s+[•●▪]\s+", text)

        for sentence in sentences:
            sentence = re.sub(r"\s+", " ", sentence).strip(" \t\r\n•●▪")
            sentence_words = _words(sentence)
            if len(sentence_words) < 4:
                continue
            key = (item.get("source", "unknown"), sentence.lower())
            if key in seen:
                continue
            direct = sentence_words & query_words
            synonym_matches = (sentence_words & expanded_words) - query_words
            # Small preference for exact query terms; reward multiple query concepts.
            score = 3 * len(direct) + len(synonym_matches)
            if score <= 0:
                continue
            seen.add(key)
            candidates.append({
                "sentence": sentence,
                "source": item.get("source", "unknown"),
                "location": item.get("location", "unknown"),
                "score": score,
                "snippet_score": float(item.get("score", 0.0)),
            })

    if not candidates:
        # Ensure the user can inspect the retrieval rather than receiving a false conclusion.
        lines = [
            "I found document passages, but could not confidently select individual sentences for this question.",
            "Here are the retrieved passages to inspect:",
        ]
        for i, item in enumerate(evidence[:3], start=1):
            lines.append(
                f"\n**[S{i}] {item.get('source', 'unknown')} — {item.get('location', 'unknown')}**\n"
                f"> {item.get('text', '')}"
            )
        return "\n".join(lines)

    candidates.sort(key=lambda x: (x["score"], x["snippet_score"]), reverse=True)

    # Select up to five distinct sentences, avoiding a response that repeats one source.
    selected: list[dict] = []
    source_counts: defaultdict[str, int] = defaultdict(int)
    for candidate in candidates:
        if source_counts[candidate["source"]] >= 4:
            continue
        selected.append(candidate)
        source_counts[candidate["source"]] += 1
        if len(selected) >= 5:
            break

    lines = [
        "### Answer from retrieved evidence",
        "",
        "No LLM API key is configured, so this answer selects relevant text from the document instead of generating a new summary.",
        "",
    ]
    for i, item in enumerate(selected, start=1):
        lines.append(
            f"- {item['sentence']} **[S{i}: {item['source']}, {item['location']}]**"
        )
    lines.extend([
        "",
        "**Note:** This extractive answer may not cover every aspect of the question. Verify important claims against the original document.",
    ])
    return "\n".join(lines)


def answer_question(question: str, evidence: list[dict]) -> str:
    """Answer a document question using an LLM when configured, otherwise citations."""
    return generate(question, evidence, "document Q&A") or evidence_only_answer(question, evidence)


def compare_documents(comparison_brief: str, evidence: list[dict]) -> str:
    """Compare retrieved information across document sources."""
    if not evidence:
        return "No relevant passages were retrieved. Upload documents or broaden the comparison brief."
    return generate(
        "Compare the documents based on this brief: " + comparison_brief
        + ". Organize by topic, identify similarities and differences, and call out missing evidence.",
        evidence,
        "cross-document comparison",
    ) or evidence_only_answer(comparison_brief, evidence)


def extract_fields(fields_text: str, evidence: list[dict]) -> dict:
    """Extract requested fields as JSON; never invent values in the fallback path."""
    fields = [line.strip(" -*\t") for line in fields_text.splitlines() if line.strip()]
    if not fields:
        fields = ["Key facts"]

    if not evidence:
        return {
            "fields": {
                field: {
                    "value": "Not found",
                    "evidence_quote": "",
                    "source": "",
                    "status": "not_found",
                }
                for field in fields
            },
            "note": "No relevant evidence was retrieved. Try a broader retrieval hint.",
        }

    llm_result = generate(
        "Extract the following fields from the evidence: " + ", ".join(fields)
        + ". Return valid JSON only, with a top-level 'fields' object. For each field include "
        + "'value' (use 'Not found' if absent), 'evidence_quote', 'source', and 'status' "
        + "('found', 'conflicting', or 'not_found'). Never guess.",
        evidence,
        "structured extraction",
    )
    if llm_result:
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", llm_result.strip(), flags=re.I)
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        return {"raw_model_output": llm_result, "warning": "The model did not return valid JSON."}

    output = {"fields": {}}
    for field in fields:
        field_words = _words(field) - _STOP_WORDS
        best = None
        best_score = 0
        for item in evidence:
            text = item.get("text", "")
            overlap = len((_words(text)) & field_words)
            if overlap > best_score:
                best, best_score = item, overlap
        found = best is not None and best_score > 0
        output["fields"][field] = {
            "value": "Review evidence manually" if found else "Not found",
            "evidence_quote": best.get("text", "")[:500] if found else "",
            "source": best.get("source", "") if found else "",
            "status": "found" if found else "not_found",
        }
    output["note"] = (
        "Heuristic fallback: configure OPENAI_API_KEY for semantic field extraction. "
        "Values are not automatically inferred."
    )
    return output


def build_report(objective: str, evidence: list[dict]) -> str:
    """Generate a cited report or an evidence inventory when no LLM is available."""
    if not evidence:
        return "# Evidence-backed report\n\nNo relevant evidence was found. Upload documents or refine the report objective."

    report = generate(
        "Create a concise business report for this objective: " + objective
        + ". Include an executive summary, key findings with citations, risks/uncertainties, "
        + "recommendations clearly labeled as recommendations, and unanswered questions.",
        evidence,
        "evidence-backed report",
    )
    if report:
        return report

    lines = [
        "# Evidence-backed report",
        "",
        f"## Objective\n{objective}",
        "",
        "## Evidence reviewed",
        "No LLM is configured, so this report lists retrieved evidence without synthesizing conclusions.",
    ]
    for i, item in enumerate(evidence, start=1):
        lines.extend([
            "",
            f"### [S{i}] {item.get('source', 'unknown')} — {item.get('location', 'unknown')}",
            item.get("text", ""),
        ])
    lines.extend([
        "",
        "## Limitations",
        "- This is an evidence inventory, not a verified business conclusion.",
        "- Review the source documents and resolve contradictions before making decisions.",
    ])
    return "\n".join(lines)
