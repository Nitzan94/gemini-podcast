# ABOUTME: Smallest possible end-to-end example — one string of source material → MP3 on disk.
# ABOUTME: Run: GEMINI_API_KEY=... uv run examples/minimal.py

"""Minimal example: pass a paragraph of source material, get an MP3.

Usage:
    export GEMINI_API_KEY=...
    uv run python examples/minimal.py
    # writes ./out.mp3
"""

from gemini_podcast import PodcastConfig, Section, generate_podcast


def main() -> None:
    result = generate_podcast(
        subject="why the QWERTY keyboard layout won",
        sections=[
            Section(
                title="Origin",
                content=(
                    "QWERTY was designed in the 1870s by Christopher Sholes for the "
                    "Sholes & Glidden typewriter, the first commercially successful "
                    "typewriter. The layout was tuned to space frequently-paired "
                    "letters apart so the mechanical typebars wouldn't jam — not, "
                    "as the common myth goes, to slow typists down."
                ),
            ),
            Section(
                title="Lock-in",
                content=(
                    "By 1888 a touch-typing champion named Frank McGurrin demonstrated "
                    "QWERTY's superiority over rival layouts in a widely-publicized "
                    "speed contest. Schools standardized on it, manufacturers followed, "
                    "and switching costs compounded — by 1920 QWERTY was effectively "
                    "the only layout taught. Dvorak's 1936 redesign showed measurable "
                    "speed gains in lab studies but never broke through the network "
                    "effect, despite multiple revival attempts."
                ),
            ),
        ],
        config=PodcastConfig(
            host_a_name="Alex",
            host_b_name="Maya",
            host_a_voice="Charon",
            host_b_voice="Aoede",
            persona_hint="two history-curious explainers, dry not breathless",
        ),
    )

    with open("out.mp3", "wb") as f:
        f.write(result.mp3_bytes)

    print(f"Wrote out.mp3 ({len(result.mp3_bytes):,} bytes, {len(result.turns)} turns)")
    print(f"Durations (ms): {result.step_durations_ms}")


if __name__ == "__main__":
    main()
