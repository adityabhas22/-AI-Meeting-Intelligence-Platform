from app.transcription.deepgram import transcribe

RESPONSE = {
    "metadata": {"duration": 5.0},
    "results": {
        "utterances": [
            {"speaker": 0, "start": 0.0, "end": 2.0, "transcript": "One."},
            {"speaker": 1, "start": 2.0, "end": 4.0, "transcript": "Two."},
        ]
    },
}


class _FakeMedia:
    def __init__(self, response: dict):
        self.response = response
        self.captured: dict = {}

    def transcribe_file(self, *, request: bytes, **kwargs):
        self.captured = {"request": request, **kwargs}
        return self.response


class _FakeClient:
    """Mimics client.listen.v1.media.transcribe_file without the network."""

    def __init__(self, response: dict):
        self.media = _FakeMedia(response)
        self.listen = type("L", (), {"v1": type("V", (), {"media": self.media})()})()


def test_transcribe_sends_expected_options_and_parses_result():
    fake = _FakeClient(RESPONSE)
    result = transcribe(b"audio-bytes", keyterms=["gRPC", "OAuth2"], client=fake)

    sent = fake.media.captured
    assert sent["request"] == b"audio-bytes"
    assert sent["model"] == "nova-3"
    assert sent["diarize_model"] == "latest"
    assert sent["utterances"] is True
    assert sent["keyterm"] == ["gRPC", "OAuth2"]
    assert result.num_speakers == 2


def test_transcribe_omits_keyterm_when_not_provided():
    fake = _FakeClient(RESPONSE)
    transcribe(b"audio", client=fake)
    assert "keyterm" not in fake.media.captured
