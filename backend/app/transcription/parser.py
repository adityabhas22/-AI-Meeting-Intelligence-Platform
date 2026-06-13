"""Turn a Deepgram prerecorded response into ordered speaker segments.

Primary source is the top-level ``utterances`` list (each entry is already a single
speaker turn). If utterances are absent we fall back to grouping consecutive
same-speaker words. Everything here is pure: it operates on the response dict so it
can be unit tested without touching the network.
"""

from app.transcription.models import TranscriptionResult, TranscriptSegment


def parse_deepgram_response(data: dict) -> TranscriptionResult:
    results = data.get("results") or {}
    segments = _segments_from_utterances(results.get("utterances") or [])
    if not segments:
        segments = _segments_from_words(_first_alternative(results).get("words") or [])

    duration = (data.get("metadata") or {}).get("duration")
    channels = results.get("channels") or []
    language = channels[0].get("detected_language") if channels else None

    return TranscriptionResult(
        segments=segments,
        duration_sec=float(duration) if duration is not None else None,
        language=language,
    )


def _segments_from_utterances(utterances: list[dict]) -> list[TranscriptSegment]:
    kept = [u for u in utterances if (u.get("transcript") or "").strip()]
    return [
        TranscriptSegment(
            idx=i,
            speaker_label=int(u.get("speaker", 0)),
            start_sec=float(u.get("start", 0.0)),
            end_sec=float(u.get("end", 0.0)),
            text=u["transcript"].strip(),
        )
        for i, u in enumerate(kept)
    ]


def _segments_from_words(words: list[dict]) -> list[TranscriptSegment]:
    segments: list[TranscriptSegment] = []
    speaker: int | None = None
    start = 0.0
    end = 0.0
    tokens: list[str] = []

    def flush() -> None:
        if tokens:
            segments.append(
                TranscriptSegment(
                    idx=len(segments),
                    speaker_label=speaker or 0,
                    start_sec=start,
                    end_sec=end,
                    text=" ".join(tokens).strip(),
                )
            )

    for w in words:
        spk = int(w.get("speaker", 0))
        token = w.get("punctuated_word") or w.get("word") or ""
        if speaker is None or spk != speaker:
            flush()
            speaker, start, end, tokens = (
                spk,
                float(w.get("start", 0.0)),
                float(w.get("end", 0.0)),
                [],
            )
        tokens.append(token)
        end = float(w.get("end", end))
    flush()
    return segments


def _first_alternative(results: dict) -> dict:
    channels = results.get("channels") or []
    if not channels:
        return {}
    alternatives = channels[0].get("alternatives") or []
    return alternatives[0] if alternatives else {}
