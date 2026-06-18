from app.indexing.embeddings import embed_texts


class _Item:
    def __init__(self, embedding: list[float]):
        self.embedding = embedding


class _FakeEmbeddings:
    def __init__(self):
        self.captured: dict = {}

    def create(self, *, model: str, input: list[str]):
        self.captured = {"model": model, "input": input}
        return type("R", (), {"data": [_Item([0.0, 0.1, 0.2]) for _ in input]})()


class _FakeClient:
    def __init__(self):
        self.embeddings = _FakeEmbeddings()


def test_embed_texts_passes_model_and_returns_one_vector_per_input():
    fake = _FakeClient()
    vectors = embed_texts(["alpha", "beta"], client=fake, model="text-embedding-3-small")
    assert fake.embeddings.captured == {
        "model": "text-embedding-3-small",
        "input": ["alpha", "beta"],
    }
    assert vectors == [[0.0, 0.1, 0.2], [0.0, 0.1, 0.2]]


def test_embed_empty_skips_the_api():
    assert embed_texts([]) == []


class _CountingEmbeddings:
    def __init__(self):
        self.calls = 0
        self.batch_sizes: list[int] = []

    def create(self, *, model: str, input: list[str]):
        self.calls += 1
        self.batch_sizes.append(len(input))
        return type("R", (), {"data": [_Item([0.0, 0.1, 0.2]) for _ in input]})()


class _CountingClient:
    def __init__(self):
        self.embeddings = _CountingEmbeddings()


def test_embed_texts_batches_large_inputs():
    fake = _CountingClient()
    texts = [f"chunk {i}" for i in range(250)]
    vectors = embed_texts(texts, client=fake, model="text-embedding-3-small")
    assert len(vectors) == 250
    assert fake.embeddings.batch_sizes == [100, 100, 50]
