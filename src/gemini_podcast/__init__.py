# ABOUTME: gemini-podcast — turn any source material into a 2-host audio podcast.
# ABOUTME: Top-level export: generate_podcast. Sub-imports: PodcastConfig, Section, VOICE_PAIRS.

from .pipeline import generate_podcast
from .script_gen import generate_script
from .synthesize import synthesize
from .encode import wav_to_mp3
from .types import PodcastConfig, PodcastResult, Section, Turn
from .voices import VOICE_PAIRS, VoicePair, all_voices

__all__ = [
    "generate_podcast",
    "generate_script",
    "synthesize",
    "wav_to_mp3",
    "PodcastConfig",
    "PodcastResult",
    "Section",
    "Turn",
    "VOICE_PAIRS",
    "VoicePair",
    "all_voices",
]

__version__ = "0.1.0"
