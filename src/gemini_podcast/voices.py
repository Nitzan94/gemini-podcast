# ABOUTME: Curated catalog of Gemini prebuilt voice pairs.
# ABOUTME: Eight contrasting pairs from the 30 available voices, ordered by recommendation strength.

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VoicePair:
    voice_a: str
    voice_b: str
    descriptor: str


# Pairs are tuned for two-host podcast dialogue. The first voice is the lead
# (more declarative); the second is the counterpart (warmer or contrasting).
# Adding a pair? Audition both voices on a 60-second sample before shipping —
# Gemini's voices vary surprisingly in noise floor and prosody.
VOICE_PAIRS: tuple[VoicePair, ...] = (
    VoicePair("Charon", "Aoede", "Informative + Breezy — NPR-style analyst & host"),
    VoicePair("Kore", "Sulafat", "Firm + Warm — anchor & approachable second"),
    VoicePair("Sadaltager", "Achird", "Knowledgeable + Friendly — expert & host"),
    VoicePair("Rasalgethi", "Callirrhoe", "Informative + Easy-going — casual explainer"),
    VoicePair("Orus", "Laomedeia", "Firm + Upbeat — energetic pairing"),
    VoicePair("Iapetus", "Vindemiatrix", "Clear + Gentle — calming long-form"),
    VoicePair("Gacrux", "Sadachbia", "Mature + Lively — older/younger contrast"),
    VoicePair("Algenib", "Erinome", "Gravelly + Clear — distinctive timbres"),
)


def all_voices() -> set[str]:
    """Flat set of every voice name referenced by VOICE_PAIRS — useful for
    validating a user-supplied PodcastConfig before sending to the API."""
    return {p.voice_a for p in VOICE_PAIRS} | {p.voice_b for p in VOICE_PAIRS}
