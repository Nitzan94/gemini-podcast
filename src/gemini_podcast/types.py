# ABOUTME: Public dataclasses — Section, PodcastConfig, Turn, PodcastResult.
# ABOUTME: All frozen so they're hashable and safe to share across threads.

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Section:
    """One chunk of source material the hosts will discuss.

    `title` shows up in the script-gen prompt so the hosts can name the
    topic naturally. `content` is the raw material — plain text, a few
    paragraphs is usually right. No upper bound, but if you push past a
    few thousand words per section the script will skim.
    """

    title: str
    content: str


@dataclass(frozen=True)
class PodcastConfig:
    """Host identity + voice + persona steering.

    `host_a_voice` and `host_b_voice` must be names from the Gemini prebuilt
    voice catalog — see voices.py for curated pairs. The two voices MUST
    differ; same-voice configs produce muddled output where you can't tell
    who is speaking.
    """

    host_a_name: str
    host_b_name: str
    host_a_voice: str
    host_b_voice: str
    persona_hint: str = ""
    # Spoken-word target. Roughly 150 words/min × 2 hosts ⇒ 1100-1500 words
    # is the 8-10 minute sweet spot. Push higher for long-form, lower for
    # quick takes.
    target_words_min: int = 1100
    target_words_max: int = 1500


@dataclass(frozen=True)
class Turn:
    """One line of dialogue. `speaker` must match `host_a_name` or
    `host_b_name` from the PodcastConfig used to generate the script."""

    speaker: str
    text: str


@dataclass(frozen=True)
class PodcastResult:
    """Returned from generate_podcast. `mp3_bytes` is the encoded audio
    ready to write to disk or upload anywhere. `step_durations_ms` is a
    breakdown for observability."""

    mp3_bytes: bytes
    turns: list[Turn]
    step_durations_ms: dict[str, int]
