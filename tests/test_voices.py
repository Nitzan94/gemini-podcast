# ABOUTME: Tests the voice catalog — no duplicates, no same-voice pairs.

from gemini_podcast.voices import VOICE_PAIRS, all_voices


def test_pairs_have_distinct_voices():
    for pair in VOICE_PAIRS:
        assert pair.voice_a != pair.voice_b, f"Pair has identical voices: {pair}"


def test_pairs_are_unique():
    pair_keys = [(p.voice_a, p.voice_b) for p in VOICE_PAIRS]
    assert len(pair_keys) == len(set(pair_keys)), "Duplicate voice pair in catalog"


def test_all_voices_returns_unique_set():
    flat = all_voices()
    assert isinstance(flat, set)
    assert len(flat) > 0
