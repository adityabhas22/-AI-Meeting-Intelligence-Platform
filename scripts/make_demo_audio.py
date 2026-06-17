"""Generate a 3-speaker meeting recording with OpenAI TTS (distinct voices), giving
the demo known ground truth for diarization and extraction. Writes demo_meeting.wav.

Usage:  uv --directory ../backend run python scripts/make_demo_audio.py [out.wav]
"""

import struct
import sys
import wave
from pathlib import Path

from openai import OpenAI

ENV = (Path(__file__).resolve().parents[1] / ".env").read_text()
KEY = next(
    line.split("=", 1)[1].strip().strip('"')
    for line in ENV.splitlines()
    if line.startswith("OPENAI_API_KEY=")
)
client = OpenAI(api_key=KEY)

SAMPLE_RATE = 24000  # gpt-4o-mini-tts pcm output

SCRIPT = [
    ("alloy", "Alright, let's start the sprint standup. Our main goal is shipping the search feature."),
    ("onyx", "On engineering, the hybrid search is working, but there's still an OAuth bug on login."),
    ("alloy", "Okay. Raj, can you fix the OAuth bug by Wednesday?"),
    ("onyx", "Yes, I'll fix the OAuth bug by Wednesday and add rate limiting to the API."),
    ("shimmer", "On design, the dashboard mockups are almost done. I can deliver them by Monday."),
    ("alloy", "Great. Let's make a decision: we ship the search feature next Friday."),
    ("onyx", "One open question, do we need rate limiting on the public API before launch?"),
    ("alloy", "Good question, let's discuss that offline. I'll email the stakeholders with the timeline."),
    ("shimmer", "Sounds good. I'll also sync with Raj on the pgvector integration for the mockups."),
    ("alloy", "Perfect. So decisions: ship search Friday, Raj fixes OAuth by Wednesday, Sara delivers mockups Monday."),
]


def silence(seconds: float) -> bytes:
    n = int(SAMPLE_RATE * seconds)
    return struct.pack("<" + "h" * n, *([0] * n))


frames = bytearray()
for i, (voice, text) in enumerate(SCRIPT):
    print(f"[{i + 1}/{len(SCRIPT)}] {voice}")
    resp = client.audio.speech.create(
        model="gpt-4o-mini-tts", voice=voice, input=text, response_format="pcm"
    )
    frames.extend(resp.read())
    frames.extend(silence(0.35))

out = sys.argv[1] if len(sys.argv) > 1 else "demo_meeting.wav"
with wave.open(out, "wb") as wav:
    wav.setnchannels(1)
    wav.setsampwidth(2)
    wav.setframerate(SAMPLE_RATE)
    wav.writeframes(bytes(frames))
print(f"wrote {out} ({len(frames) / 2 / SAMPLE_RATE:.1f}s)")
