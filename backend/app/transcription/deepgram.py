"""Deepgram nova-3 adapter. Thin wrapper: call the API, hand the response dict to
the (pure, tested) parser. The client is injectable so tests never hit the network."""

import json
from typing import Any

from deepgram import DeepgramClient

from app.config import get_settings
from app.transcription.models import TranscriptionResult
from app.transcription.parser import parse_deepgram_response

# nova-3 with utterances gives ready-made speaker turns; keyterm carries technical
# vocabulary (nova-3 only). smart_format handles numbers, dates, and the like.
_BASE_OPTIONS: dict[str, Any] = {
    "model": "nova-3",
    "diarize_model": "latest",  # batch diarization v2; enables and supersedes `diarize`
    "smart_format": True,
    "punctuate": True,
    "utterances": True,
    "paragraphs": True,
}


def transcribe(
    audio: bytes,
    *,
    keyterms: list[str] | None = None,
    client: DeepgramClient | None = None,
) -> TranscriptionResult:
    client = client or DeepgramClient(api_key=get_settings().deepgram_api_key)
    options = dict(_BASE_OPTIONS)
    if keyterms:
        options["keyterm"] = keyterms
    response = client.listen.v1.media.transcribe_file(request=audio, **options)
    return parse_deepgram_response(_to_dict(response))


def _to_dict(response: Any) -> dict:
    if isinstance(response, dict):
        return response
    dump = getattr(response, "model_dump", None)
    if callable(dump):
        return dump(mode="json")
    to_json = getattr(response, "json", None)
    if callable(to_json):
        return json.loads(to_json())
    raise TypeError(f"cannot convert Deepgram response of type {type(response)!r} to dict")
