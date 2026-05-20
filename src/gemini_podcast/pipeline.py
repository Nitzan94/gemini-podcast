# ABOUTME: Top-level orchestrator — script_gen → synthesize → encode.
# ABOUTME: Single entry point: generate_podcast(subject, sections, config) → PodcastResult.

from __future__ import annotations

import logging
import time
from typing import Iterable

from google import genai

from .encode import wav_to_mp3
from .script_gen import generate_script
from .synthesize import synthesize
from .types import PodcastConfig, PodcastResult, Section
from .voices import all_voices

logger = logging.getLogger(__name__)


def _validate_config(config: PodcastConfig) -> None:
    if not config.host_a_name or not config.host_b_name:
        raise ValueError("PodcastConfig requires non-empty host names")
    if config.host_a_name == config.host_b_name:
        raise ValueError("host_a_name and host_b_name must differ")
    if config.host_a_voice == config.host_b_voice:
        raise ValueError(
            "host_a_voice and host_b_voice must differ — same voice "
            "produces muddled output where you can't tell who is speaking"
        )
    known = all_voices()
    for label, v in [("host_a_voice", config.host_a_voice), ("host_b_voice", config.host_b_voice)]:
        if v not in known:
            logger.warning(
                "pipeline: %s=%r is not in the curated VOICE_PAIRS catalog. "
                "It may still work if Gemini accepts the name, but the pair "
                "hasn't been auditioned for podcast-grade prosody.",
                label, v,
            )


def generate_podcast(
    subject: str,
    sections: Iterable[Section],
    config: PodcastConfig,
    *,
    client: genai.Client | None = None,
) -> PodcastResult:
    """Run the full pipeline: script generation → TTS → MP3 encode.

    `subject` is a one-line description of what the podcast is about
    (e.g. "Stripe's payment moat" or "the history of chess engines").
    It shows up directly in the script-gen prompt and shapes the hosts'
    framing.

    `sections` is the source material — pass an iterable of Section
    objects. The hosts will discuss what's in them; they're told not to
    invent facts beyond what you provide.

    `client` lets you inject a pre-built `genai.Client` (e.g. with
    Vertex AI auth). If omitted, a client is built from `GEMINI_API_KEY`.

    Returns a `PodcastResult` with mp3_bytes, the dialogue turns (handy
    for transcripts), and per-step timings.

    Requires `ffmpeg` on PATH.
    """
    _validate_config(config)
    section_list = list(sections)
    if not section_list:
        raise ValueError("At least one Section is required")

    client = client or genai.Client()
    durations: dict[str, int] = {}

    t0 = time.monotonic()
    turns = generate_script(subject, section_list, config, client=client)
    durations["script_gen"] = int((time.monotonic() - t0) * 1000)

    t0 = time.monotonic()
    wav_bytes = synthesize(turns, config, client=client)
    durations["synthesize"] = int((time.monotonic() - t0) * 1000)

    t0 = time.monotonic()
    mp3_bytes = wav_to_mp3(wav_bytes)
    durations["encode"] = int((time.monotonic() - t0) * 1000)

    logger.info(
        "pipeline: done subject=%r turns=%d mp3=%d bytes durations=%s",
        subject, len(turns), len(mp3_bytes), durations,
    )
    return PodcastResult(
        mp3_bytes=mp3_bytes,
        turns=turns,
        step_durations_ms=durations,
    )
