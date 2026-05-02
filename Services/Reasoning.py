# Reasoning.py

import os
import json
import re
from dotenv import load_dotenv
from groq import Groq
try:
    from .STT import transcribe_audio
except ImportError:
    from STT import transcribe_audio

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def extract_json(text: str):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else None

def generate_clinical_report(file_path: str, patient_context: dict | None = None) -> dict:
    # STEP 1: Get transcript from STT
    transcript = transcribe_audio(file_path)

    if not transcript:
        raise ValueError("Empty transcript from STT")

    patient_context = patient_context or {}
    patient_name = patient_context.get("name")
    patient_age = patient_context.get("age")
    patient_gender = patient_context.get("gender")

    # STEP 2: LLM prompt
    prompt = f"""
You are a clinical medical assistant.

Convert the following transcript into a structured medical report.
Use patient demographic details from the database as the source of truth.

Return ONLY valid JSON in this format:

{{
  "patient_name": {json.dumps(patient_name)},
  "age": {json.dumps(patient_age)},
  "gender": {json.dumps(patient_gender)},
  "symptoms": [],
  "diagnosis": null,
  "medications": [],
  "dosage": [],
  "precautions": [],
  "doctor_notes": null
}}

Rules:
- Output strictly JSON (no explanation)
- Keep everything in English
- Keep patient_name, age, and gender exactly aligned with the database context
- If any non-demographic field is missing, return null or empty list
- Do not hallucinate
-igonre any kind conversation which does not pertain to the medical report or not relevant to report generation

Database patient context:
{json.dumps(patient_context, ensure_ascii=False)}

Transcript:
{transcript}
"""

    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    raw_output = response.choices[0].message.content

    json_text = extract_json(raw_output)
    if not json_text:
        raise ValueError("Invalid JSON from LLM")

    report = json.loads(json_text)

    if patient_name is not None:
        report["patient_name"] = patient_name
    if patient_age is not None:
        report["age"] = patient_age
    if patient_gender is not None:
        report["gender"] = patient_gender

    return report


# Optional: direct run test
if __name__ == "__main__":
    file_path = input("Enter audio file path: ").strip()
    result = generate_clinical_report(file_path)
    print("\nFinal Structured Report:\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))
