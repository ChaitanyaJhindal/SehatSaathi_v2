import os
import tempfile
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr

from Services.db_service import (
    DatabaseConfigError,
    authenticate_doctor,
    create_doctor_account,
    create_report_record,
    get_patient_details,
    upsert_patient_record,
)
from Services.Reasoning import generate_clinical_report
from Services.pdf_service import generate_pdf

app = FastAPI(title="SehatSaathi API", version="1.0.0")

# In-memory PDF cache for demo use; not durable across restarts.
_PDF_CACHE: dict[str, dict[str, str]] = {}
_PDF_TTL = timedelta(hours=2)


class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    specialization: str | None = None
    organization_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


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


def _build_patient_context(
    *,
    doctor_id: str | None,
    patient_id: str | None,
    patient_name: str | None,
    patient_age: str | None,
    patient_gender: str | None,
    patient_phone: str | None,
    patient_notes: str | None,
) -> dict:
    if patient_id:
        return get_patient_details(patient_id)

    if not patient_name:
        return {}

    return upsert_patient_record(
        doctor_id,
        {
            "name": patient_name,
            "age": patient_age,
            "gender": patient_gender,
            "phone": patient_phone,
            "notes": patient_notes,
        },
    )


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/auth/signup")
async def signup(payload: SignupRequest):
    try:
        doctor = create_doctor_account(
            name=payload.name,
            email=payload.email,
            password=payload.password,
            specialization=payload.specialization,
            organization_name=payload.organization_name,
        )
    except DatabaseConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to create account.") from exc

    return doctor


@app.post("/auth/login")
async def login(payload: LoginRequest):
    try:
        doctor = authenticate_doctor(payload.email, payload.password)
    except DatabaseConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "No account" in detail else 401
        raise HTTPException(status_code=status_code, detail=detail) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to login.") from exc

    return doctor


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
    patient_id: str | None = Form(None),
    doctor_id: str | None = Form(None),
    patient_name: str | None = Form(None),
    patient_age: str | None = Form(None),
    patient_gender: str | None = Form(None),
    patient_phone: str | None = Form(None),
    patient_notes: str | None = Form(None),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Audio file is required.")

    patient = {}
    if patient_id or patient_name:
        try:
            patient = _build_patient_context(
                doctor_id=doctor_id,
                patient_id=patient_id,
                patient_name=patient_name,
                patient_age=patient_age,
                patient_gender=patient_gender,
                patient_phone=patient_phone,
                patient_notes=patient_notes,
            )
        except DatabaseConfigError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail="Failed to resolve patient details.") from exc

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

    report["doctor_id"] = doctor_id
    report["patient_id"] = patient.get("id")
    report["doctor_name"] = patient.get("doctor_name")
    if patient.get("phone"):
        report["patient_phone"] = patient.get("phone")
    if patient.get("notes"):
        report["patient_notes"] = patient.get("notes")

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

    if patient:
        try:
            create_report_record(report, patient, pdf_url=f"/report/download/{token}")
        except Exception:
            pass

    return {
        "filename": file.filename,
        "transcript": report.get("transcript", ""),
        "report": report,
        "pdf_download_url": f"/report/download/{token}",
        "patient_id": patient.get("id"),
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
