# End-to-end test: signup/login -> /generate-report -> PDF download
# Run with: .venv\Scripts\python.exe test_report.py <path-to-audio>

import json
import os
import sys
import time
import uuid
import requests

AUDIO_PATH = sys.argv[1] if len(sys.argv) > 1 else os.getenv("TEST_AUDIO_PATH", "")
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000").rstrip("/")
PDF_OUT = "test_output_report.pdf"


def step(msg):
    print("\n" + "=" * 60)
    print(">>  " + msg)
    print("=" * 60)


if not AUDIO_PATH or not os.path.exists(AUDIO_PATH):
    print("Usage: .venv\\Scripts\\python.exe test_report.py <audio-file-path>")
    print("Or set TEST_AUDIO_PATH in the environment.")
    sys.exit(1)

# 1. Health
step("1 / 4  Checking server health")
r = requests.get(f"{BASE_URL}/health", timeout=10)
print(f"Status: {r.status_code}  Body: {r.json()}")
assert r.status_code == 200, "Server not healthy!"

# 2. Authenticate
step("2 / 4  Authenticating test doctor account")
email = f"test_{uuid.uuid4().hex[:8]}@sehatsaathi.local"
auth_resp = requests.post(
    f"{BASE_URL}/auth/signup",
    json={
        "name": "Dr. Test Doctor",
        "email": email,
        "password": "TestPassword123",
        "specialization": "General Medicine",
        "organization_name": "SehatSaathi Test Clinic",
    },
    timeout=15,
)
assert auth_resp.status_code == 200, f"Signup failed: {auth_resp.text}"
token = auth_resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 3. Generate report
step("3 / 4  Uploading audio -> generating report (30-90s)")
start = time.time()
with open(AUDIO_PATH, "rb") as audio_file:
    resp = requests.post(
        f"{BASE_URL}/generate-report",
        headers=headers,
        files={"file": (os.path.basename(AUDIO_PATH), audio_file, "audio/mpeg")},
        data={"patient_name": "Test Patient", "patient_age": "35", "patient_gender": "Male"},
        timeout=300,
    )

elapsed = time.time() - start
print(f"\nHTTP {resp.status_code}  (took {elapsed:.1f}s)")

if resp.status_code != 200:
    print("ERROR RESPONSE:")
    print(resp.text)
    sys.exit(1)

payload = resp.json()
print("\nReport JSON received:")
print(json.dumps(payload.get("report", {}), indent=2, ensure_ascii=False))
print(f"\nPDF download URL: {payload.get('pdf_download_url')}")

# 4. Download PDF
step("4 / 4  Downloading PDF")
pdf_url = payload.get("pdf_download_url", "")
if not pdf_url.startswith("http"):
    pdf_url = BASE_URL + pdf_url

pdf_resp = requests.get(pdf_url, timeout=30)
print(f"PDF HTTP {pdf_resp.status_code}  Size: {len(pdf_resp.content):,} bytes")

if pdf_resp.status_code == 200:
    with open(PDF_OUT, "wb") as f:
        f.write(pdf_resp.content)
    print(f"\nPDF saved to: {PDF_OUT}")
else:
    print("PDF download failed:", pdf_resp.text)
    sys.exit(1)

print("\nALL STEPS PASSED.")
