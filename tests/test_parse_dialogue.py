# ABOUTME: Tests _parse_dialogue — the JSON-array → list[Turn] parser.
# ABOUTME: Covers the LLM output shapes that drift in production.

import json

import pytest

from gemini_podcast.script_gen import _parse_dialogue


def _make(turns: list[tuple[str, str]]) -> str:
    return json.dumps([{"speaker": s, "text": t} for s, t in turns])


def test_clean_dialogue_parses():
    raw = _make([("Alex", "hi"), ("Maya", "hello"), ("Alex", "good"), ("Maya", "bye")])
    turns = _parse_dialogue(raw, "Alex", "Maya")
    assert len(turns) == 4
    assert turns[0].speaker == "Alex"


def test_strips_markdown_code_fence():
    raw = "```json\n" + _make([("Alex", "a"), ("Maya", "b"), ("Alex", "c"), ("Maya", "d")]) + "\n```"
    turns = _parse_dialogue(raw, "Alex", "Maya")
    assert len(turns) == 4


def test_rejects_unknown_speaker():
    raw = _make([("Alex", "a"), ("Stranger", "b"), ("Alex", "c"), ("Maya", "d")])
    with pytest.raises(ValueError, match="not in"):
        _parse_dialogue(raw, "Alex", "Maya")


def test_rejects_monologue():
    # Only Alex speaks
    raw = _make([("Alex", "a"), ("Alex", "b"), ("Alex", "c"), ("Alex", "d")])
    with pytest.raises(ValueError, match="expected both"):
        _parse_dialogue(raw, "Alex", "Maya")


def test_rejects_too_short():
    raw = _make([("Alex", "a"), ("Maya", "b")])
    with pytest.raises(ValueError, match="too short"):
        _parse_dialogue(raw, "Alex", "Maya")


def test_rejects_non_array_root():
    raw = json.dumps({"speaker": "Alex", "text": "hi"})
    with pytest.raises(ValueError, match="Expected JSON array"):
        _parse_dialogue(raw, "Alex", "Maya")


def test_skips_empty_text():
    raw = _make([("Alex", "a"), ("Maya", ""), ("Alex", "c"), ("Maya", "d"), ("Alex", "e")])
    turns = _parse_dialogue(raw, "Alex", "Maya")
    # Empty turn dropped, rest kept
    assert len(turns) == 4
    assert all(t.text for t in turns)
