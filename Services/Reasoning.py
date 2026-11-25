import json
import logging
import os
import re
from typing import Any

from dotenv import load_dotenv
from groq import Groq

try:
    from .STT import transcribe_audio
except ImportError:
    from STT import transcribe_audio

load_dotenv()

logger = logging.getLogger("sehatsaathi.reasoning")

_groq_client: Groq | None = None


def _get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is not None:
        return _groq_client

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured in the environment.")

    _groq_client = Groq(api_key=api_key)
    return _groq_client


def extract_json(text: str | None) -> str | None:
    if not text:
        return None
    cleaned = text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", cleaned, re.DOTALL)
    if fence_match:
        return fence_match.group(1)

    start = cleaned.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False
    for idx in range(start, len(cleaned)):
        ch = cleaned[idx]
        if escaped:
            escaped = False
            continue
        if ch == "\\" and in_string:
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return cleaned[start : idx + 1]

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    return match.group(0) if match else None


def _to_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item or "").strip()]
    if isinstance(value, str):
        return [line.strip() for line in value.splitlines() if line.strip()]
    text = str(value).strip()
    return [text] if text else []


def _to_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "; ".join(str(v).strip() for v in value if str(v or "").strip())
    return str(value).strip()


def _parse_llm_json(raw_output: str | None) -> dict[str, Any]:
    if not raw_output:
        raise ValueError("Empty response from LLM.")
    try:
        parsed = json.loads(raw_output)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    json_text = extract_json(raw_output)
    if not json_text:
        raise ValueError("Invalid JSON from LLM.")
    parsed = json.loads(json_text)
    if not isinstance(parsed, dict):
        raise ValueError("LLM JSON root must be an object.")
    return parsed


def generate_clinical_report(file_path: str, patient_context: dict | None = None) -> dict[str, Any]:
    transcript = transcribe_audio(file_path)

    if not transcript:
        raise ValueError("Empty transcript from STT")

    patient_context = patient_context or {}
    patient_name = patient_context.get("name")
    patient_age = patient_context.get("age")
    patient_gender = patient_context.get("gender")
    patient_phone = patient_context.get("phone")
    patient_notes = patient_context.get("notes")

    prompt = f"""
You are a clinical medical assistant.

Extract medical information from the doctor-patient conversation below.
Write all values in clear clinical English (translate regional/Hindi phrases to English while keeping exact medication names and dosages).

Return ONLY a valid JSON object with these exact keys:
- "symptoms": list of strings
- "diagnosis": string (or empty string if unclear)
- "medications": list of strings (each as "MedicineName - Strength/Frequency" if known)
- "dosage": list of strings (specific dosage/timing/duration instructions, one instruction per item)
- "precautions": list of strings
- "follow_up": string (follow-up instructions or timeframe if mentioned, else empty string)
- "doctor_notes": string (concise clinical summary/notes)

If a list field has no entries return []. If a string field is missing return "".

Conversation:
{transcript}
"""

    client = _get_groq_client()
    model_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"},
        )
    except Exception as exc:
        logger.warning("Groq call with json_object failed (%s); retrying plain completion.", exc)
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )

    raw_output = response.choices[0].message.content if response.choices else None
    raw_report = _parse_llm_json(raw_output)

    report: dict[str, Any] = {
        "symptoms": _to_str_list(raw_report.get("symptoms")),
        "diagnosis": _to_str(raw_report.get("diagnosis")),
        "medications": _to_str_list(raw_report.get("medications")),
        "dosage": _to_str_list(raw_report.get("dosage")),
        "precautions": _to_str_list(raw_report.get("precautions")),
        "follow_up": _to_str(raw_report.get("follow_up")),
        "doctor_notes": _to_str(raw_report.get("doctor_notes")),
        "transcript": transcript,
    }

    if patient_name is not None:
        report["patient_name"] = patient_name
    if patient_age is not None:
        report["age"] = patient_age
        report["patient_age"] = patient_age
    if patient_gender is not None:
        report["gender"] = patient_gender
        report["patient_gender"] = patient_gender
    if patient_phone is not None:
        report["patient_phone"] = patient_phone
        report["patient_mobile"] = patient_phone
    if patient_notes is not None:
        report["patient_notes"] = patient_notes

    return report


if __name__ == "__main__":
    audio_path = input("Enter audio file path: ").strip()
    result = generate_clinical_report(audio_path)
    print("\nFinal Structured Report:\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))
