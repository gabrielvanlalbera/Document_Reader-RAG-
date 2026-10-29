from src.retrieval import TfidfRetriever


def test_retriever_finds_relevant_document():
    chunks = [
        {"id": "1", "text": "Refunds are available within thirty days.", "source": "refund.txt", "location": "text"},
        {"id": "2", "text": "The company was founded in 2012 in Odisha.", "source": "about.txt", "location": "text"},
    ]
    retriever = TfidfRetriever()
    retriever.fit(chunks)
    results = retriever.search("refund policy days", top_k=2)
    assert results
    assert results[0]["source"] == "refund.txt"


def test_empty_retriever_is_safe():
    retriever = TfidfRetriever()
    retriever.fit([])
    assert retriever.search("anything") == []
