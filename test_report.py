# End-to-end test: audio -> /generate-report -> PDF download
# Run with: .venv\Scripts\python.exe test_report.py

import io
import json
import sys
import time
import requests

AUDIO_PATH = r"C:\Users\Chait\Downloads\doctor_patient_check.mpeg"
BASE_URL    = "http://localhost:8000"
PDF_OUT     = "test_output_report.pdf"


def step(msg):
    print("\n" + "="*60)
    print(">>  " + msg)
    print("="*60)


# ── STEP 1: Health ──────────────────────────────────────────────
step("1 / 3  Checking server health")
r = requests.get(f"{BASE_URL}/health", timeout=10)
print(f"Status: {r.status_code}  Body: {r.json()}")
assert r.status_code == 200, "Server not healthy!"


# ── STEP 2: Generate report ─────────────────────────────────────
step("2 / 3  Uploading audio → generating report  (this takes ~30–90 s)")

start = time.time()
with open(AUDIO_PATH, "rb") as audio_file:
    resp = requests.post(
        f"{BASE_URL}/generate-report",
        files={"file": ("doctor_patient_check.mpeg", audio_file, "audio/mpeg")},
        timeout=300,   # Sarvam STT job can take a while
    )

elapsed = time.time() - start
print(f"\nHTTP {resp.status_code}  (took {elapsed:.1f}s)")

if resp.status_code != 200:
    print("❌  ERROR RESPONSE:")
    try:
        print(json.dumps(resp.json(), indent=2))
    except Exception:
        print(resp.text)
    sys.exit(1)

payload = resp.json()
print("\n✅  Report JSON received:")
print(json.dumps(payload.get("report", {}), indent=2, ensure_ascii=False))
print(f"\nTranscript preview:\n{str(payload.get('transcript',''))[:400]}")
print(f"\nPDF download URL: {payload.get('pdf_download_url')}")


# ── STEP 3: Download PDF ────────────────────────────────────────
step("3 / 3  Downloading PDF")

pdf_url = payload.get("pdf_download_url", "")
if not pdf_url.startswith("http"):
    pdf_url = BASE_URL + pdf_url

pdf_resp = requests.get(pdf_url, timeout=30)
print(f"PDF HTTP {pdf_resp.status_code}  Size: {len(pdf_resp.content):,} bytes")

if pdf_resp.status_code == 200:
    with open(PDF_OUT, "wb") as f:
        f.write(pdf_resp.content)
    print(f"\n✅  PDF saved to: {PDF_OUT}")
else:
    print("❌  PDF download failed:")
    print(pdf_resp.text)
    sys.exit(1)

print("\n🎉  ALL STEPS PASSED — pipeline is working end-to-end!\n")
