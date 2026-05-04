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

Extract medical information from the conversation.
STRICT RULES (MUST FOLLOW):

Extract ONLY information that is explicitly stated in the conversation.
DO NOT infer, assume, or add any new medical information.
DO NOT correct, reinterpret, or expand statements.
If something is unclear, ambiguous, or contradictory → return null for that field.
DO NOT guess missing dosage, duration, frequency, or diagnosis.
Preserve original meaning exactly as spoken.
If multiple conflicting values exist → include both OR return null (do not resolve conflict).
DO NOT add medical knowledge from outside the conversation.
DO NOT hallucinate body parts, symptoms, or conditions.
If a medication is mentioned without dosage → include only the name.
If dosage format is incomplete → copy exactly as given, do not fix it.
Keep output strictly grounded in transcript text only.
Return ONLY valid JSON.

Fields:
symptoms        (list of strings)
diagnosis       (string)
medications     (list of strings, each as "MedicineName - Dosage")
dosage          (string, general dosage notes if any)
precautions     (list of strings)
follow_up       (string, follow-up instructions or date if mentioned)
doctor_notes    (string)

If information is missing return null.

Conversation:
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

    report["transcript"] = transcript
    report["transcript"] = transcript

    return report


# Optional: direct run test
if __name__ == "__main__":
    file_path = input("Enter audio file path: ").strip()
    result = generate_clinical_report(file_path)
    print("\nFinal Structured Report:\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))
