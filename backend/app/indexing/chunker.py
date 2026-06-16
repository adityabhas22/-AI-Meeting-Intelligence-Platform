"""Group speaker turns into retrieval chunks. Pure and deterministic so it is fully
unit testable. Chunks keep speaker labels inline (good context for the embedder and
for the model reading retrieved passages) and carry a timestamp span for citations."""

from pydantic import BaseModel

from app.transcription.models import TranscriptSegment

TARGET_CHARS = 1000
OVERLAP_SEGMENTS = 1


class Chunk(BaseModel):
    idx: int
    text: str
    start_sec: float
    end_sec: float


def chunk_segments(
    segments: list[TranscriptSegment],
    *,
    target_chars: int = TARGET_CHARS,
    overlap: int = OVERLAP_SEGMENTS,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    current: list[TranscriptSegment] = []
    size = 0

    for seg in segments:
        if current and size + len(seg.text) > target_chars:
            chunks.append(_build(current, len(chunks)))
            current = current[-overlap:] if overlap else []
            size = sum(len(s.text) for s in current)
        current.append(seg)
        size += len(seg.text)

    if current:
        chunks.append(_build(current, len(chunks)))
    return chunks


def _build(segments: list[TranscriptSegment], idx: int) -> Chunk:
    text = "\n".join(f"Speaker {s.speaker_label}: {s.text}" for s in segments)
    return Chunk(idx=idx, text=text, start_sec=segments[0].start_sec, end_sec=segments[-1].end_sec)
