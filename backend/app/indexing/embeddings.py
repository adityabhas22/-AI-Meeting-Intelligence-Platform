"""Embed text with OpenAI. Client injectable so tests never call the API."""

from openai import OpenAI

from app.config import get_settings

# Keep each request well under the API's per-call input limit on long recordings.
_BATCH_SIZE = 100


def embed_texts(
    texts: list[str],
    *,
    client: OpenAI | None = None,
    model: str | None = None,
) -> list[list[float]]:
    if not texts:
        return []
    settings = get_settings()
    client = client or OpenAI(api_key=settings.openai_api_key)
    model = model or settings.openai_embedding_model

    vectors: list[list[float]] = []
    for start in range(0, len(texts), _BATCH_SIZE):
        batch = texts[start : start + _BATCH_SIZE]
        response = client.embeddings.create(model=model, input=batch)
        vectors.extend(item.embedding for item in response.data)
    return vectors
