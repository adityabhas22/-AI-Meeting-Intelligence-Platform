from pydantic import BaseModel


class TranscriptSegment(BaseModel):
    """One speaker turn: a contiguous stretch of speech by a single speaker."""

    idx: int
    speaker_label: int
    start_sec: float
    end_sec: float
    text: str


class TranscriptionResult(BaseModel):
    segments: list[TranscriptSegment]
    duration_sec: float | None = None
    language: str | None = None

    @property
    def num_speakers(self) -> int:
        return len({s.speaker_label for s in self.segments})

    def labelled_text(self) -> str:
        """Full transcript with speaker labels, used as the LLM extraction input."""
        return "\n".join(f"Speaker {s.speaker_label}: {s.text}" for s in self.segments)
