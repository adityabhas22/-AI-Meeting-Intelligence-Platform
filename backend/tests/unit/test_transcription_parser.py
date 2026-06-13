from app.transcription.parser import parse_deepgram_response

UTTERANCE_RESPONSE = {
    "metadata": {"duration": 12.34},
    "results": {
        "channels": [{"detected_language": "en", "alternatives": [{"transcript": "full"}]}],
        "utterances": [
            {
                "speaker": 0,
                "start": 0.0,
                "end": 3.2,
                "transcript": "Welcome everyone to the standup.",
            },
            {
                "speaker": 1,
                "start": 3.5,
                "end": 6.0,
                "transcript": "  Thanks, I pushed the auth fix.  ",
            },
            {
                "speaker": 2,
                "start": 6.2,
                "end": 9.0,
                "transcript": "I will review the gRPC change.",
            },
            {"speaker": 0, "start": 9.1, "end": 9.1, "transcript": "   "},
        ],
    },
}


def test_utterances_become_ordered_segments():
    result = parse_deepgram_response(UTTERANCE_RESPONSE)
    assert [s.idx for s in result.segments] == [0, 1, 2]  # empty utterance dropped + reindexed
    assert [s.speaker_label for s in result.segments] == [0, 1, 2]
    assert result.segments[1].text == "Thanks, I pushed the auth fix."  # stripped
    assert result.segments[0].start_sec == 0.0
    assert result.segments[2].end_sec == 9.0


def test_metadata_duration_speakers_and_language():
    result = parse_deepgram_response(UTTERANCE_RESPONSE)
    assert result.duration_sec == 12.34
    assert result.language == "en"
    assert result.num_speakers == 3


def test_labelled_text_format():
    result = parse_deepgram_response(UTTERANCE_RESPONSE)
    assert result.labelled_text() == (
        "Speaker 0: Welcome everyone to the standup.\n"
        "Speaker 1: Thanks, I pushed the auth fix.\n"
        "Speaker 2: I will review the gRPC change."
    )


WORDS_RESPONSE = {
    "results": {
        "channels": [
            {
                "alternatives": [
                    {
                        "words": [
                            {
                                "word": "hello",
                                "punctuated_word": "Hello",
                                "start": 0.0,
                                "end": 0.4,
                                "speaker": 0,
                            },
                            {
                                "word": "there",
                                "punctuated_word": "there.",
                                "start": 0.4,
                                "end": 0.9,
                                "speaker": 0,
                            },
                            {
                                "word": "hi",
                                "punctuated_word": "Hi",
                                "start": 1.2,
                                "end": 1.5,
                                "speaker": 1,
                            },
                            {
                                "word": "again",
                                "punctuated_word": "again.",
                                "start": 1.5,
                                "end": 1.9,
                                "speaker": 1,
                            },
                        ]
                    }
                ]
            }
        ]
    }
}


def test_falls_back_to_word_grouping_when_no_utterances():
    result = parse_deepgram_response(WORDS_RESPONSE)
    assert len(result.segments) == 2
    assert result.segments[0].speaker_label == 0
    assert result.segments[0].text == "Hello there."  # prefers punctuated_word
    assert result.segments[0].start_sec == 0.0
    assert result.segments[0].end_sec == 0.9
    assert result.segments[1].speaker_label == 1
    assert result.segments[1].text == "Hi again."


def test_empty_response_yields_no_segments():
    result = parse_deepgram_response({})
    assert result.segments == []
    assert result.num_speakers == 0
    assert result.duration_sec is None
