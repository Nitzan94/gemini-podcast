# ABOUTME: WAV → MP3 via ffmpeg subprocess. Requires ffmpeg on PATH.
# ABOUTME: Returns MP3 bytes; raises if ffmpeg is missing or encoding fails.

from __future__ import annotations

import logging
import shutil
import subprocess

logger = logging.getLogger(__name__)


def wav_to_mp3(wav_bytes: bytes, bitrate_kbps: int = 96) -> bytes:
    """Encode WAV → MP3 with libmp3lame.

    96 kbps mono at 24kHz is plenty for spoken audio — same range as
    NotebookLM. Doubling that only inflates file size, no audible win.

    Requires the `ffmpeg` binary on PATH. On macOS: `brew install ffmpeg`.
    In a Dockerfile: `RUN apt-get install -y ffmpeg`.
    """
    if not wav_bytes:
        raise ValueError("Empty WAV input")
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "ffmpeg not found on PATH. Install with `brew install ffmpeg` "
            "(macOS), `apt-get install ffmpeg` (Debian/Ubuntu), or add it "
            "to your container image."
        )

    cmd = [
        "ffmpeg",
        "-loglevel", "error",
        "-y",
        "-f", "wav",
        "-i", "pipe:0",
        "-codec:a", "libmp3lame",
        "-b:a", f"{bitrate_kbps}k",
        "-f", "mp3",
        "pipe:1",
    ]
    result = subprocess.run(cmd, input=wav_bytes, capture_output=True, check=True)
    if not result.stdout:
        raise RuntimeError("ffmpeg produced no MP3 output")
    logger.info(
        "encode: WAV %d bytes → MP3 %d bytes (%dkbps)",
        len(wav_bytes),
        len(result.stdout),
        bitrate_kbps,
    )
    return result.stdout
