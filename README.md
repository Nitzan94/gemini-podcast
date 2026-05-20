# gemini-podcast

Turn any source material into a **two-host audio podcast** using Gemini multi-speaker TTS. Same shape as Google's NotebookLM audio overviews — feed it text, get an MP3 with two named hosts riffing on it.

```python
from gemini_podcast import PodcastConfig, Section, generate_podcast

result = generate_podcast(
    subject="why the QWERTY keyboard layout won",
    sections=[
        Section(title="Origin", content="QWERTY was designed in 1870s by..."),
        Section(title="Lock-in", content="By 1888 a touch-typing contest..."),
    ],
    config=PodcastConfig(
        host_a_name="Alex", host_a_voice="Charon",
        host_b_name="Maya", host_b_voice="Aoede",
        persona_hint="two history-curious explainers, dry not breathless",
    ),
)

with open("out.mp3", "wb") as f:
    f.write(result.mp3_bytes)
```

That's the whole API. Bring your own source material, get MP3 bytes back. No storage assumptions, no opinions about your stack — write to disk, upload to S3/GCS/R2, stream over a websocket, whatever fits.

## Why this exists

Gemini ships multi-speaker TTS with a clean API, but stringing it into a *podcast-shaped* output is awkward enough that most starter code stops at "single voice reading a paragraph". The real work is in three places:

1. **Script generation that doesn't read like an essay.** A dialogue prompt that pins the speaker labels to host names, forbids filler ("great point", "what's fascinating"), and tells the model not to invent facts beyond the source. Without these the model defaults to a single-voice TED-style monologue split mechanically across two labels.
2. **Chunking around the quality-drift cliff.** Gemini's multi-speaker TTS degrades past ~3 minutes of continuous dialogue — voices drift, pacing wobbles. This library chunks at speaker boundaries to keep each call under a 450-word budget, then concatenates the raw PCM (safe because every chunk shares sample rate / width / channels) before wrapping in one WAV header.
3. **A WAV→MP3 step that actually runs.** Spoken audio doesn't need 320kbps stereo; 96kbps mono at 24kHz is the NotebookLM range and produces files that are small enough to email.

You can read all three concerns in ~300 lines of Python. The point of the package is that you don't have to.

## Install

```sh
uv pip install gemini-podcast
# or
pip install gemini-podcast
```

You also need **ffmpeg** on PATH:

```sh
brew install ffmpeg                  # macOS
apt-get install -y ffmpeg            # Debian/Ubuntu
# in a Dockerfile:  RUN apt-get install -y ffmpeg
```

And a Gemini API key:

```sh
export GEMINI_API_KEY=...
```

## Run the minimal example

```sh
uv run python examples/minimal.py
# → writes out.mp3 (~1.5 MB, 60–90 sec depending on dialogue length)
```

## More examples

- **`examples/minimal.py`** — string input → MP3 on disk.
- **`examples/from_url.py`** — fetch a webpage, extract readable text, turn it into a podcast.
- **`examples/upload_to_gcs.py`** — generate then upload to Google Cloud Storage with a public URL.

All three show the same library; the only thing changing is *what you feed it* and *where the bytes go*.

## API

### `generate_podcast(subject, sections, config, *, client=None) → PodcastResult`

| Arg | Type | Notes |
|---|---|---|
| `subject` | `str` | One-line description (e.g. `"Stripe's payment moat"`). Goes into the script-gen prompt. |
| `sections` | `Iterable[Section]` | Source material the hosts will discuss. Pass titled chunks for clean topic transitions. |
| `config` | `PodcastConfig` | Host names + voices + persona hint. See [voices](#voices). |
| `client` | `genai.Client \| None` | Optional. Pass a pre-built client to use Vertex AI auth; default builds from `GEMINI_API_KEY`. |

Returns `PodcastResult(mp3_bytes, turns, step_durations_ms)`.

### `Section(title, content)`

Plain dataclass. `title` shows up in the prompt so hosts can name the topic naturally. `content` is the raw text — paragraphs work, no upper bound but past a few thousand words per section the script will skim.

### `PodcastConfig`

```python
PodcastConfig(
    host_a_name: str,
    host_b_name: str,
    host_a_voice: str,           # Gemini prebuilt voice name
    host_b_voice: str,           # must differ from host_a_voice
    persona_hint: str = "",      # one-line steering for the script
    target_words_min: int = 1100,
    target_words_max: int = 1500,
)
```

The two voices MUST differ — same-voice configs produce muddled output where you can't tell who's speaking. The library validates this and raises before calling the API.

### Voices

Eight curated voice pairs ship in `gemini_podcast.VOICE_PAIRS`, ordered by recommendation strength:

```python
from gemini_podcast import VOICE_PAIRS
for p in VOICE_PAIRS:
    print(p.voice_a, p.voice_b, "—", p.descriptor)
```

```
Charon     Aoede        — Informative + Breezy — NPR-style analyst & host
Kore       Sulafat      — Firm + Warm — anchor & approachable second
Sadaltager Achird       — Knowledgeable + Friendly — expert & host
Rasalgethi Callirrhoe   — Informative + Easy-going — casual explainer
Orus       Laomedeia    — Firm + Upbeat — energetic pairing
Iapetus    Vindemiatrix — Clear + Gentle — calming long-form
Gacrux     Sadachbia    — Mature + Lively — older/younger contrast
Algenib    Erinome      — Gravelly + Clear — distinctive timbres
```

You can pass any Gemini prebuilt voice name (full list in [the Gemini docs](https://ai.google.dev/gemini-api/docs/speech-generation#voices)) — the curated pairs are just the ones I auditioned and found to work well together.

### Lower-level pieces

If you want to assemble the pipeline yourself (cache scripts, regenerate audio with a different voice pair, etc.):

```python
from gemini_podcast import generate_script, synthesize, wav_to_mp3

turns = generate_script(subject, sections, config)
wav_bytes = synthesize(turns, config)
mp3_bytes = wav_to_mp3(wav_bytes)
```

## Models + env vars

| Env var | Default | What it controls |
|---|---|---|
| `GEMINI_API_KEY` | (required) | Auth for both script-gen and TTS. |
| `GEMINI_PODCAST_SCRIPT_MODEL` | `gemini-2.5-pro` | Script-gen model. Pro produces the best dialogue; Flash drops execs and specifics. |
| `GEMINI_PODCAST_TTS_MODEL` | `gemini-2.5-flash-preview-tts` | The TTS model. Multi-speaker requires `*-tts` variants. |

## Tests

```sh
uv run pytest
```

The tests are pure-unit — chunking boundaries, dialogue parser edge cases, voice catalog consistency. They don't hit the Gemini API. For an end-to-end smoke test, run `examples/minimal.py` with a real `GEMINI_API_KEY` and listen to the output.

## License

MIT. See `LICENSE`.

## Credits

Built by Nitzan Bar-Ness while shipping audio-podcast generation inside Sago. Same recipe, generalized so you can drop it into anything that has text.
