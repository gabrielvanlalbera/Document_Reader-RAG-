from src.chunking import split_text, build_chunks


def test_split_text_preserves_content():
    text = "alpha beta gamma delta epsilon zeta eta theta"
    chunks = split_text(text, chunk_size=20, overlap=5)
    assert len(chunks) > 1
    assert all(chunk.strip() for chunk in chunks)


def test_build_chunks_retains_metadata():
    chunks = build_chunks([{"text": "A short document.", "source": "demo.txt", "location": "text"}], 100, 10)
    assert chunks[0]["source"] == "demo.txt"
    assert chunks[0]["location"] == "text"
    assert chunks[0]["id"] == "doc1"
