from app.services.chunking import _split_paragraphs, chunk_page, chunk_pages


def test_chunks_never_cross_page_boundaries():
    page1 = "alpha " * 40
    page2 = "beta " * 40
    chunks = chunk_pages([(1, page1), (2, page2)], size=25, overlap=5)
    assert chunks, "expected some chunks"
    for c in chunks:
        assert c.page in (1, 2)
        if c.page == 1:
            assert "beta" not in c.text
        else:
            assert "alpha" not in c.text


def test_overlap_is_carried_between_chunks():
    words = [f"w{i}" for i in range(600)]
    chunks = chunk_page(" ".join(words), size=200, overlap=40)
    assert len(chunks) >= 3
    assert all(len(c.split()) <= 200 for c in chunks)
    assert chunks[1].split()[:40] == chunks[0].split()[-40:]


def test_numbered_clauses_become_separate_paragraphs():
    text = "2.1 Annual leave. Full-time staff get 24 days.\n2.2 Carry forward. Up to 5 days carry over."
    paras = _split_paragraphs(text)
    assert len(paras) == 2
    assert paras[0].startswith("2.1") and paras[1].startswith("2.2")


def test_skips_short_and_number_only_chunks():
    pages = [(1, "Page 3"), (2, "12 34 56 78 90 11 12 13 14 15 16 17")]
    assert chunk_pages(pages, size=200, overlap=20) == []


def test_no_duplicate_overlap_only_chunk_at_end():
    words = " ".join(f"w{i}" for i in range(200))  # exactly one full chunk
    assert len(chunk_page(words, size=200, overlap=40)) == 1
