# ABOUTME: Gemini multi-speaker TTS — turn a list of Turn into WAV bytes.
# ABOUTME: Chunks long dialogues at speaker boundaries to stay under quality-drift threshold.

from __future__ import annotations

import io
import logging
import os
import wave
from typing import Iterable

from google import genai
from google.genai import types as genai_types

from .types import PodcastConfig, Turn

logger = logging.getLogger(__name__)

# Gemini multi-speaker TTS output: signed-16-bit PCM, 24kHz mono. These are
# fixed by the model output format — don't change without re-reading the
# google-genai docs and verifying the bit depth.
_PCM_SAMPLE_RATE = 24_000
_PCM_SAMPLE_WIDTH = 2  # bytes per sample
_PCM_CHANNELS = 1

# Output quality drifts past "a few minutes" of dialogue per Gemini docs.
# ~450 words ≈ 3 minutes of two-host pacing — keeps each TTS call inside
# the safe zone. Raise cautiously; lower if you hear distortion.
_CHUNK_WORD_BUDGET = 450

_TTS_MODEL = os.getenv("GEMINI_PODCAST_TTS_MODEL", "gemini-2.5-flash-preview-tts")


def _format_chunk_text(turns: list[Turn]) -> str:
    # "Name: text" — speaker labels MUST match MultiSpeakerVoiceConfig
    # speaker fields exactly, otherwise voices won't bind.
    return "\n".join(f"{t.speaker}: {t.text}" for t in turns)


def _chunk_turns(turns: Iterable[Turn]) -> list[list[Turn]]:
    chunks: list[list[Turn]] = []
    current: list[Turn] = []
    current_words = 0
    for turn in turns:
        words = len(turn.text.split())
        if current and current_words + words > _CHUNK_WORD_BUDGET:
            chunks.append(current)
            current = []
            current_words = 0
        current.append(turn)
        current_words += words
    if current:
        chunks.append(current)
    return chunks


def _synthesize_chunk(
    turns: list[Turn],
    config: PodcastConfig,
    client: genai.Client,
) -> bytes:
    response = client.models.generate_content(
        model=_TTS_MODEL,
        contents=_format_chunk_text(turns),
        config=genai_types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=genai_types.SpeechConfig(
                multi_speaker_voice_config=genai_types.MultiSpeakerVoiceConfig(
                    speaker_voice_configs=[
                        genai_types.SpeakerVoiceConfig(
                            speaker=config.host_a_name,
                            voice_config=genai_types.VoiceConfig(
                                prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(
                                    voice_name=config.host_a_voice,
                                ),
                            ),
                        ),
                        genai_types.SpeakerVoiceConfig(
                            speaker=config.host_b_name,
                            voice_config=genai_types.VoiceConfig(
                                prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(
                                    voice_name=config.host_b_voice,
                                ),
                            ),
                        ),
                    ],
                ),
            ),
        ),
    )

    # Empty candidates usually means a safety block or quota exhaustion —
    # surface prompt_feedback so the caller sees *why* instead of IndexError.
    if not response.candidates:
        feedback = getattr(response, "prompt_feedback", None)
        raise RuntimeError(
            f"Gemini TTS returned no candidates ({len(turns)} turns) — "
            f"possible safety block or quota; prompt_feedback={feedback!r}"
        )

    parts = response.candidates[0].content.parts
    for part in parts:
        if part.inline_data and part.inline_data.data:
            return part.inline_data.data
    raise RuntimeError(
        "Gemini TTS returned no inline audio data — check model + response_modalities"
    )


def _wrap_pcm_as_wav(pcm: bytes) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(_PCM_CHANNELS)
        wav.setsampwidth(_PCM_SAMPLE_WIDTH)
        wav.setframerate(_PCM_SAMPLE_RATE)
        wav.writeframes(pcm)
    return buf.getvalue()


def synthesize(
    turns: list[Turn],
    config: PodcastConfig,
    *,
    client: genai.Client | None = None,
) -> bytes:
    """Render dialogue to a single WAV blob.

    Chunks at speaker boundaries to stay within Gemini's quality-drift
    threshold, then concatenates raw PCM before wrapping in one WAV
    header. PCM concat is safe because every chunk shares sample rate /
    width / channel count.
    """
    if not turns:
        raise ValueError("No dialogue turns to synthesize")

    client = client or genai.Client()
    chunks = _chunk_turns(turns)
    logger.info(
        "synthesize: %d turns → %d chunks, voices=(%s/%s)",
        len(turns),
        len(chunks),
        config.host_a_voice,
        config.host_b_voice,
    )

    pcm_parts: list[bytes] = []
    for i, chunk in enumerate(chunks):
        logger.info("synthesize: chunk %d/%d (%d turns)", i + 1, len(chunks), len(chunk))
        pcm_parts.append(_synthesize_chunk(chunk, config, client))

    return _wrap_pcm_as_wav(b"".join(pcm_parts))
