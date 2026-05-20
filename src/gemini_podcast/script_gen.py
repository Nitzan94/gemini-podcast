# ABOUTME: Source material → 2-host dialogue script via Gemini Pro.
# ABOUTME: Generic prompt — works for any subject (research briefs, news roundups, explainers, fiction).

from __future__ import annotations

import json
import logging
import os
import re
from typing import Iterable

from google import genai
from google.genai import types as genai_types

from .types import PodcastConfig, Section, Turn

logger = logging.getLogger(__name__)


_SCRIPT_MODEL = os.getenv("GEMINI_PODCAST_SCRIPT_MODEL", "gemini-2.5-pro")


def _build_prompt(
    subject: str,
    sections: list[Section],
    config: PodcastConfig,
) -> str:
    section_blocks = "\n\n".join(
        f"### {s.title}\n{s.content}" for s in sections
    )
    scope_label = (
        "the full source material"
        if len(sections) > 3
        else f"these sections: {', '.join(s.title for s in sections)}"
    )
    persona_line = (
        f"PERSONA: {config.persona_hint}\n\n" if config.persona_hint else ""
    )

    return f"""You are writing a two-host podcast script about: {subject}.

{persona_line}HOSTS (use these exact names as speaker labels):
- {config.host_a_name} — leads the conversation; introduces topics; asks the sharpest follow-up.
- {config.host_b_name} — analytical counterpart; brings specific numbers, dates, names; pushes back when claims feel thin.

SCOPE: Cover {scope_label}. Do not invent facts not present in the source. If the source omits something, omit it from the script.

LENGTH: {config.target_words_min}-{config.target_words_max} words of dialogue (excluding labels). Pace naturally; do not pad.

STYLE RULES:
- Open with a 1-2 sentence cold intro from {config.host_a_name}, no greeting or "welcome back".
- Hosts cite specifics by name (people, numbers, dates) — never vague references like "the founder" or "the company".
- Skip filler like "great point", "absolutely", "what's fascinating".
- End with a one-line beat that gives the listener a take to chew on. No sign-off, no outro music cue.
- No music, sound effects, or stage directions. Plain dialogue only.

OUTPUT FORMAT — strict JSON array of turn objects, no markdown, no commentary:
[
  {{"speaker": "{config.host_a_name}", "text": "..."}},
  {{"speaker": "{config.host_b_name}", "text": "..."}},
  ...
]

SOURCE MATERIAL:

{section_blocks}
"""


_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _parse_dialogue(raw: str, host_a: str, host_b: str) -> list[Turn]:
    cleaned = _JSON_FENCE_RE.sub("", raw).strip()
    data = json.loads(cleaned)
    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array, got {type(data).__name__}")
    allowed = {host_a, host_b}
    turns: list[Turn] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Turn {i} is not an object")
        speaker = str(item.get("speaker", "")).strip()
        text = str(item.get("text", "")).strip()
        if speaker not in allowed:
            raise ValueError(
                f"Turn {i} speaker '{speaker}' not in {sorted(allowed)}"
            )
        if not text:
            continue
        turns.append(Turn(speaker=speaker, text=text))
    if len(turns) < 4:
        raise ValueError(f"Dialogue too short ({len(turns)} turns)")
    speakers_used = {t.speaker for t in turns}
    if speakers_used != allowed:
        raise ValueError(
            f"Dialogue uses only {speakers_used}, expected both {allowed}"
        )
    return turns


def generate_script(
    subject: str,
    sections: Iterable[Section],
    config: PodcastConfig,
    *,
    client: genai.Client | None = None,
) -> list[Turn]:
    """Turn source material into a two-host dialogue. Raises on malformed output.

    `client` lets callers inject a pre-configured genai.Client (e.g. with
    Vertex AI auth). If omitted, a client is built from GEMINI_API_KEY.
    """
    section_list = list(sections)
    if not section_list:
        raise ValueError("No sections provided for script generation")

    prompt = _build_prompt(subject, section_list, config)
    client = client or genai.Client()
    response = client.models.generate_content(
        model=_SCRIPT_MODEL,
        contents=prompt,
        config=genai_types.GenerateContentConfig(
            temperature=0.4,
            response_mime_type="application/json",
        ),
    )
    raw = response.text or ""
    if not raw:
        raise RuntimeError("Empty response from script-gen LLM")

    turns = _parse_dialogue(raw, config.host_a_name, config.host_b_name)
    logger.info(
        "script_gen: %d turns (~%d words) for subject=%r",
        len(turns),
        sum(len(t.text.split()) for t in turns),
        subject,
    )
    return turns
