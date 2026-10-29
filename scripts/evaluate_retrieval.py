from pathlib import Path
from src.ingestion import parse_uploaded_file
from src.chunking import build_chunks
from src.retrieval import TfidfRetriever
from src.evaluation import recall_at_k, reciprocal_rank

ROOT = Path(__file__).resolve().parents[1]
sample_dir = ROOT / "sample_data"
records = []
for path in sample_dir.glob("*.txt"):
    records.extend(parse_uploaded_file(path.name, path.read_bytes()))
chunks = build_chunks(records, chunk_size=700, overlap=80)
retriever = TfidfRetriever()
retriever.fit(chunks)

cases = [
    ("refund period and eligibility", {"acme_refund_policy.txt"}),
    ("quarter one sales and revenue", {"acme_q1_summary.txt"}),
    ("company business and headquarters", {"acme_company_overview.txt"}),
]
print("Retrieval smoke test")
print("=" * 60)
scores = []
for query, relevant in cases:
    hits = retriever.search(query, top_k=3)
    sources = [h["source"] for h in hits]
    recall = recall_at_k(sources, relevant, 3)
    rr = reciprocal_rank(sources, relevant)
    scores.append((recall, rr))
    print(f"\nQuery: {query}")
    print(f"Expected: {sorted(relevant)}")
    print(f"Top sources: {sources}")
    print(f"Recall@3: {recall:.2f} | Reciprocal rank: {rr:.2f}")
print("\nMean Recall@3:", round(sum(s[0] for s in scores) / len(scores), 3))
print("Mean reciprocal rank:", round(sum(s[1] for s in scores) / len(scores), 3))
