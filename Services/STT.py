import json
import logging
import os
import shutil
import tempfile
import time
from uuid import uuid4

from dotenv import load_dotenv
from sarvamai import SarvamAI

load_dotenv()

logger = logging.getLogger("sehatsaathi.stt")

_sarvam_client: SarvamAI | None = None


def _candidate_api_keys() -> list[str]:
    keys: list[str] = []
    for env_name in ("SARVAM_API_KEY", "SARVAM_FALLBACK_API_KEY"):
        val = (os.getenv(env_name) or "").strip()
        if val and val not in keys:
            keys.append(val)
    return keys


def _get_sarvam_client(api_key: str | None = None) -> SarvamAI:
    global _sarvam_client
    if api_key:
        return SarvamAI(api_subscription_key=api_key)

    if _sarvam_client is not None:
        return _sarvam_client

    keys = _candidate_api_keys()
    if not keys:
        raise RuntimeError("SARVAM_API_KEY is not configured in the environment.")

    _sarvam_client = SarvamAI(api_subscription_key=keys[0])
    return _sarvam_client


def _format_transcript(transcript_data: dict) -> str:
    diarized = transcript_data.get("diarized_transcript")
    if isinstance(diarized, dict):
        entries = diarized.get("entries") or []
        lines: list[str] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            utterance = " ".join(str(entry.get("transcript") or "").split())
            if not utterance:
                continue
            speaker = entry.get("speaker_id") or entry.get("speaker")
            if speaker is not None and str(speaker).strip():
                lines.append(f"Speaker {speaker}: {utterance}")
            else:
                lines.append(utterance)
        if lines:
            return "\n".join(lines)

    transcript = str(transcript_data.get("transcript") or "")
    return " ".join(transcript.split())


MAX_DIARIZATION_SPEAKERS = 20


def _resolve_num_speakers() -> int | None:
    raw = (os.getenv("SARVAM_NUM_SPEAKERS") or "").strip().lower()
    if raw == "auto":
        return None
    if not raw:
        return MAX_DIARIZATION_SPEAKERS
    try:
        parsed = int(raw)
    except ValueError:
        return MAX_DIARIZATION_SPEAKERS
    return max(1, min(parsed, MAX_DIARIZATION_SPEAKERS))


def _transcribe_with_client(client: SarvamAI, file_path: str, timeout_seconds: int) -> str:
    num_speakers = _resolve_num_speakers()
    job_kwargs = {
        "model": "saaras:v3",
        "mode": "transcribe",
        "language_code": "unknown",
        "with_diarization": True,
    }
    if num_speakers is not None:
        job_kwargs["num_speakers"] = num_speakers

    job = client.speech_to_text_job.create_job(**job_kwargs)

    job.upload_files(file_paths=[file_path])
    time.sleep(2)
    job.start()

    try:
        job.wait_until_complete(poll_interval=3, timeout=timeout_seconds)
    except TypeError:
        job.wait_until_complete()

    file_results = job.get_file_results() or {}
    successful = file_results.get("successful") or []
    failed = file_results.get("failed") or []

    if not successful:
        if failed:
            detail = failed[0].get("error_message") or failed[0].get("error") or str(failed[0])
            logger.error("Sarvam STT failed for %s: %s", file_path, detail)
            raise RuntimeError(f"Audio transcription failed: {detail}")
        raise RuntimeError("Audio transcription returned no output.")

    output_dir = os.path.join(tempfile.gettempdir(), f"ss_stt_{uuid4().hex}")
    os.makedirs(output_dir, exist_ok=True)

    try:
        job.download_outputs(output_dir=output_dir)
        output_file = os.path.join(output_dir, successful[0]["file_name"] + ".json")
        with open(output_file, "r", encoding="utf-8") as f:
            transcript_data = json.load(f)
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)

    return _format_transcript(transcript_data)


def transcribe_audio(file_path: str, timeout_seconds: int = 240) -> str:
    keys = _candidate_api_keys()
    if not keys:
        raise RuntimeError("SARVAM_API_KEY is not configured in the environment.")

    last_exc: Exception | None = None
    for idx, api_key in enumerate(keys):
        try:
            client = _get_sarvam_client(api_key=api_key)
            return _transcribe_with_client(client, file_path, timeout_seconds)
        except Exception as exc:
            last_exc = exc
            if idx + 1 < len(keys):
                logger.warning("Primary Sarvam STT key failed (%s); retrying with fallback key.", exc)
            else:
                raise

    raise last_exc  # pragma: no cover
