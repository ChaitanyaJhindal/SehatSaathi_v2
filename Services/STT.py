# stt_service.py

from sarvamai import SarvamAI
from dotenv import load_dotenv
import os
import time
import json

load_dotenv()

sarvam = SarvamAI(api_subscription_key=os.getenv("SARVAM_API_KEY"))

def transcribe_audio(file_path: str) -> str:
    job = sarvam.speech_to_text_job.create_job(
        model="saaras:v3",
        mode="transcribe",
        language_code="unknown",
        with_diarization=True,
        num_speakers=2
    )

    job.upload_files(file_paths=[file_path])
    time.sleep(2)
    job.start()
    job.wait_until_complete()

    file_results = job.get_file_results()

    if len(file_results["successful"]) == 0:
        return ""

    job.download_outputs(output_dir="./output")

    output_file = os.path.join(
        "./output",
        file_results["successful"][0]["file_name"] + ".json"
    )

    with open(output_file, "r", encoding="utf-8") as f:
        transcript_data = json.load(f)

    transcript = transcript_data.get("transcript", "")
    transcript = " ".join(transcript.split())

    return transcript