# ABOUTME: Show how to wire the MP3 to a storage backend (GCS here, but the
# ABOUTME: shape is the same for S3, R2, Supabase Storage, anywhere).

"""End-to-end: generate a podcast, upload to GCS, return a public URL.

The library returns MP3 bytes intentionally — no storage assumptions, no
opinions about your bucket layout. Wire it however you want; this is one
example.

Requires: `pip install google-cloud-storage`.
"""

import os

from google.cloud import storage  # type: ignore

from gemini_podcast import PodcastConfig, Section, generate_podcast


def upload_mp3(mp3_bytes: bytes, bucket_name: str, blob_path: str) -> str:
    client = storage.Client()
    blob = client.bucket(bucket_name).blob(blob_path)
    blob.upload_from_string(mp3_bytes, content_type="audio/mpeg")
    return f"https://storage.googleapis.com/{bucket_name}/{blob_path}"


def main() -> None:
    bucket = os.environ["BUCKET_NAME"]

    result = generate_podcast(
        subject="serverless cold starts",
        sections=[
            Section(
                title="What they are",
                content=(
                    "A cold start is the latency added when a serverless platform "
                    "spins up a fresh execution environment to handle a request. "
                    "It includes container provisioning, language runtime init, "
                    "and any user-level bootstrap code."
                ),
            ),
            Section(
                title="Why they hurt",
                content=(
                    "Cold start latency varies from ~50ms (Cloudflare Workers V8 "
                    "isolates) to several seconds (a JVM container on Lambda). For "
                    "interactive APIs the user-perceived hit is brutal — and harder "
                    "to mitigate as your function gets heavier."
                ),
            ),
        ],
        config=PodcastConfig(
            host_a_name="Alex",
            host_b_name="Maya",
            host_a_voice="Sadaltager",
            host_b_voice="Achird",
        ),
    )

    url = upload_mp3(result.mp3_bytes, bucket, "podcasts/cold-starts.mp3")
    print(f"Uploaded: {url}")


if __name__ == "__main__":
    main()
