# ABOUTME: Tests _chunk_turns — speaker-boundary chunking for the 450-word budget.
# ABOUTME: Pure unit tests, no API calls.

from gemini_podcast.synthesize import _chunk_turns
from gemini_podcast.types import Turn


def _word_count(turns: list[Turn]) -> int:
    return sum(len(t.text.split()) for t in turns)


def test_single_short_turn_is_one_chunk():
    turns = [Turn("Alex", "hello world")]
    chunks = _chunk_turns(turns)
    assert len(chunks) == 1
    assert chunks[0] == turns


def test_under_budget_stays_one_chunk():
    turns = [
        Turn("Alex", "word " * 100),
        Turn("Maya", "word " * 100),
        Turn("Alex", "word " * 100),
    ]
    chunks = _chunk_turns(turns)
    assert len(chunks) == 1


def test_over_budget_rolls_to_next_chunk():
    # Each turn is 200 words; three turns = 600 > 450 budget
    turns = [
        Turn("Alex", "word " * 200),
        Turn("Maya", "word " * 200),
        Turn("Alex", "word " * 200),
    ]
    chunks = _chunk_turns(turns)
    assert len(chunks) >= 2
    # No chunk should exceed the budget (except a single oversized turn)
    for chunk in chunks:
        if len(chunk) > 1:
            assert _word_count(chunk) <= 450


def test_single_oversized_turn_stays_alone():
    # One turn larger than the budget — should not be split (we chunk at
    # speaker boundaries only, never mid-turn).
    big = Turn("Alex", "word " * 600)
    chunks = _chunk_turns([big])
    assert len(chunks) == 1
    assert chunks[0] == [big]


def test_empty_input_returns_empty():
    assert _chunk_turns([]) == []
