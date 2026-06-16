from app.indexing.chunker import chunk_segments
from app.transcription.models import TranscriptSegment


def seg(idx: int, spk: int, start: float, end: float, text: str) -> TranscriptSegment:
    return TranscriptSegment(idx=idx, speaker_label=spk, start_sec=start, end_sec=end, text=text)


def test_small_input_is_a_single_chunk():
    segs = [seg(0, 0, 0.0, 1.0, "Hello there"), seg(1, 1, 1.0, 2.0, "Hi back")]
    chunks = chunk_segments(segs, target_chars=1000)
    assert len(chunks) == 1
    assert chunks[0].idx == 0
    assert chunks[0].text == "Speaker 0: Hello there\nSpeaker 1: Hi back"
    assert chunks[0].start_sec == 0.0
    assert chunks[0].end_sec == 2.0


def test_splits_into_multiple_chunks_with_one_segment_overlap():
    segs = [seg(i, i % 2, float(i), float(i + 1), f"word{i} " * 5) for i in range(6)]
    chunks = chunk_segments(segs, target_chars=40, overlap=1)
    assert len(chunks) > 1
    # overlap: the last line of each chunk reappears as the first line of the next
    for a, b in zip(chunks, chunks[1:], strict=False):
        assert a.text.splitlines()[-1] == b.text.splitlines()[0]
    assert [c.idx for c in chunks] == list(range(len(chunks)))
    assert chunks[0].start_sec == 0.0


def test_empty_segments_produce_no_chunks():
    assert chunk_segments([]) == []
