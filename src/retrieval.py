"""Simple, local TF-IDF retrieval baseline."""
from __future__ import annotations
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class TfidfRetriever:
    def __init__(self):
        self.chunks: list[dict] = []
        self.vectorizer = None
        self.matrix = None

    def fit(self, chunks: list[dict]) -> None:
        self.chunks = list(chunks)
        if not self.chunks:
            self.vectorizer, self.matrix = None, None
            return
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=100_000)
        self.matrix = self.vectorizer.fit_transform([c["text"] for c in self.chunks])

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        if not query.strip() or self.matrix is None:
            return []
        query_vector = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vector, self.matrix).ravel()
        ranked = scores.argsort()[::-1][:max(0, top_k)]
        results = []
        for index in ranked:
            if scores[index] <= 0:
                continue
            item = dict(self.chunks[index])
            item["score"] = float(scores[index])
            results.append(item)
        return results
