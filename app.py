import os
import tempfile
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from Services.db_service import (
    DatabaseConfigError,
    create_report_record,
    get_patient_details,
)
from Services.Reasoning import generate_clinical_report
from Services.pdf_service import generate_pdf

app = FastAPI(title="SehatSaathi API", version="1.0.0")

# In-memory PDF cache for demo use; not durable across restarts.
_PDF_CACHE: dict[str, dict[str, str]] = {}
_PDF_TTL = timedelta(hours=2)


def _cleanup_files(paths: list[str]) -> None:
    for path in paths:
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except OSError:
            pass


def _purge_expired_pdfs() -> None:
    now = datetime.utcnow()
    expired = [key for key, value in _PDF_CACHE.items()
               if now - datetime.fromisoformat(value["created_at"]) > _PDF_TTL]
    for key in expired:
        entry = _PDF_CACHE.pop(key, None)
        if entry:
            _cleanup_files([entry.get("path")])


def _cache_pdf(path: str) -> str:
    token = uuid4().hex
    _PDF_CACHE[token] = {
        "path": path,
        "created_at": datetime.utcnow().isoformat(),
    }
    return token


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/report/pdf")
async def create_report_pdf(
    background_tasks: BackgroundTasks,
    patient_id: str = Form(...),
    audio: UploadFile = File(...)
):
    if not audio.filename:
        raise HTTPException(status_code=400, detail="Audio file is required.")

    try:
        patient = get_patient_details(patient_id)
    except DatabaseConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch patient details.") from exc

    suffix = os.path.splitext(audio.filename)[1] or ".wav"
    temp_dir = tempfile.gettempdir()
    audio_path = os.path.join(temp_dir, f"ss_audio_{uuid4().hex}{suffix}")

    with open(audio_path, "wb") as f:
        content = await audio.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty audio file.")
        f.write(content)

    try:
        report = generate_clinical_report(audio_path, patient_context=patient)
    except Exception as exc:
        _cleanup_files([audio_path])
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    report_id = str(uuid4())
    report["id"] = report_id
    report["report_id"] = report_id
    report["patient_id"] = patient.get("id")
    report["doctor_name"] = patient.get("doctor_name")

    pdf_name = f"clinical_report_{uuid4().hex}.pdf"
    pdf_path = os.path.join(temp_dir, pdf_name)

    try:
        generate_pdf(report, pdf_path)
    except Exception as exc:
        _cleanup_files([audio_path, pdf_path])
        raise HTTPException(status_code=500, detail="Failed to generate PDF.") from exc

    try:
        create_report_record(report, patient)
    except Exception as exc:
        _cleanup_files([audio_path, pdf_path])
        raise HTTPException(status_code=500, detail=f"Failed to save report: {exc}") from exc

    background_tasks.add_task(_cleanup_files, [audio_path, pdf_path])

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename="clinical_report.pdf"
    )


@app.post("/generate-report")
async def generate_report(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    patient_id: str | None = Form(None)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Audio file is required.")

    patient = {}
    if patient_id:
        try:
            patient = get_patient_details(patient_id)
        except DatabaseConfigError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail="Failed to fetch patient details.") from exc

    suffix = os.path.splitext(file.filename)[1] or ".wav"
    temp_dir = tempfile.gettempdir()
    audio_path = os.path.join(temp_dir, f"ss_audio_{uuid4().hex}{suffix}")

    with open(audio_path, "wb") as f:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty audio file.")
        f.write(content)

    try:
        report = generate_clinical_report(audio_path, patient_context=patient)
    except Exception as exc:
        _cleanup_files([audio_path])
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    pdf_name = f"clinical_report_{uuid4().hex}.pdf"
    pdf_path = os.path.join(temp_dir, pdf_name)

    try:
        generate_pdf(report, pdf_path)
    except Exception as exc:
        _cleanup_files([audio_path, pdf_path])
        raise HTTPException(status_code=500, detail="Failed to generate PDF.") from exc

    _purge_expired_pdfs()
    token = _cache_pdf(pdf_path)
    background_tasks.add_task(_cleanup_files, [audio_path])

    return {
        "filename": file.filename,
        "transcript": report.get("transcript", ""),
        "report": report,
        "pdf_download_url": f"/report/download/{token}",
    }


@app.get("/report/download/{token}")
async def download_report(token: str):
    _purge_expired_pdfs()
    entry = _PDF_CACHE.get(token)
    if not entry:
        raise HTTPException(status_code=404, detail="PDF not found or expired.")

    return FileResponse(
        entry["path"],
        media_type="application/pdf",
        filename="clinical_report.pdf"
    )
