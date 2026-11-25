import logging
import os
import re
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import jwt
from fastapi import BackgroundTasks, Body, Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr

from Services.Reasoning import generate_clinical_report
from Services.db_service import (
    AuthError,
    ConflictError,
    DatabaseConfigError,
    NotFoundError,
    ValidationError,
    authenticate_doctor,
    create_doctor_account,
    create_report_record,
    get_doctor_by_id,
    get_patient_details,
    get_report_record,
    list_doctor_reports,
    update_report_record,
    upsert_patient_record,
)
from Services.pdf_service import generate_pdf
from Services.whatsapp_service import (
    WhatsAppConfigError,
    WhatsAppNotConnectedError,
    WhatsAppValidationError,
    connect_whatsapp_session,
    get_whatsapp_status,
    is_whatsapp_enabled,
    logout_whatsapp_session,
    request_whatsapp_pairing_code,
    send_report_whatsapp_message,
    stop_whatsapp_bridge,
)

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("sehatsaathi.api")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(BASE_DIR, "output", "pdfs")
DIST_DIR = os.path.join(BASE_DIR, "dist")
os.makedirs(PDF_DIR, exist_ok=True)

MAX_AUDIO_BYTES = 25 * 1024 * 1024  # 25 MB
_TOKEN_RE = re.compile(r"^(?:[a-fA-F0-9]{24,64}|[a-fA-F0-9-]{36})$")

_DEFAULT_DEV_SECRET = "sehatsaathi-dev-jwt-secret-change-in-production"
_JWT_SECRET = os.getenv("JWT_SECRET") or _DEFAULT_DEV_SECRET
if _JWT_SECRET == _DEFAULT_DEV_SECRET:
    logger.warning("JWT_SECRET is not set; using development fallback secret.")
_JWT_ALGORITHM = "HS256"
_JWT_TTL_HOURS = int(os.getenv("JWT_TTL_HOURS", "168"))

@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    stop_whatsapp_bridge()


app = FastAPI(title="SehatSaathi API", version="2.0.0", lifespan=lifespan)

_cors_origins_env = os.getenv("CORS_ORIGINS", "*").strip()
_cors_origins = [origin.strip() for origin in _cors_origins_env.split(",") if origin.strip()] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


class UpdateReportRequest(BaseModel):
    symptoms: list[str] | str | None = None
    diagnosis: str | None = None
    medications: list[str] | str | None = None
    dosage: list[str] | str | None = None
    precautions: list[str] | str | None = None
    follow_up: str | None = None
    doctor_notes: str | None = None
    patient_name: str | None = None
    patient_age: int | str | None = None
    patient_gender: str | None = None
    patient_phone: str | None = None
    patient_notes: str | None = None
    visit_type: str | None = None


class PairingCodeRequest(BaseModel):
    phone: str


class SendWhatsAppRequest(BaseModel):
    phone: str | None = None


def _cleanup_files(paths: list[str]) -> None:
    for path in paths:
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except OSError:
            pass


def _purge_expired_pdfs() -> None:
    now = datetime.now(timezone.utc)
    expired = []
    for key, value in list(_PDF_CACHE.items()):
        try:
            created_at = datetime.fromisoformat(value["created_at"])
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            if now - created_at > _PDF_TTL:
                expired.append(key)
        except Exception:
            expired.append(key)
    for key in expired:
        _PDF_CACHE.pop(key, None)


def _cache_pdf(path: str, token: str | None = None) -> str:
    token = token or uuid4().hex
    _PDF_CACHE[token] = {
        "path": path,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return token


def _safe_pdf_path(token: str) -> str:
    if not _TOKEN_RE.fullmatch(token or ""):
        raise HTTPException(status_code=400, detail="Invalid report token.")
    pdf_root = os.path.abspath(PDF_DIR)
    candidate = os.path.abspath(os.path.join(pdf_root, f"clinical_report_{token}.pdf"))
    if os.path.commonpath([pdf_root, candidate]) != pdf_root:
        raise HTTPException(status_code=400, detail="Invalid report token.")
    return candidate


def _extract_token_from_pdf_url(pdf_url: str | None) -> str | None:
    if not pdf_url:
        return None
    token = pdf_url.rstrip("/").split("/")[-1].split("?")[0]
    if _TOKEN_RE.fullmatch(token):
        return token
    return None


def _absolute_url(request: Request, path_or_url: str | None) -> str | None:
    if not path_or_url:
        return None
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        return path_or_url

    token = path_or_url.split("/")[-1]
    base_url = None
    env_public = os.getenv("PUBLIC_BASE_URL")
    if env_public:
        base_url = env_public.rstrip("/")
    else:
        forwarded_host = request.headers.get("x-forwarded-host")
        if forwarded_host:
            proto = request.headers.get("x-forwarded-proto", "https")
            base_url = f"{proto}://{forwarded_host}"
        else:
            host = request.headers.get("host", "")
            if "localhost" in host or "127.0.0.1" in host:
                try:
                    import urllib.request

                    with urllib.request.urlopen("http://127.0.0.1:20241/metrics", timeout=0.5) as r:
                        m = re.search(r'userHostname="(https://[^"]+)"', r.read().decode("utf-8"))
                        if m:
                            base_url = m.group(1).rstrip("/")
                except Exception as exc:
                    logger.debug("Cloudflare tunnel metrics not available: %s", exc)

    if not base_url:
        base_url = str(request.base_url).rstrip("/")

    return f"{base_url}/report/download/{token}"


def _create_access_token(doctor: dict[str, Any]) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(doctor["id"]),
        "email": doctor.get("email"),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=_JWT_TTL_HOURS)).timestamp()),
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)


def get_current_doctor(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authentication required.")

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required.")

    try:
        claims = jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid authentication token.") from exc

    doctor_id = claims.get("sub")
    if not doctor_id:
        raise HTTPException(status_code=401, detail="Invalid authentication token.")

    try:
        doctor = get_doctor_by_id(doctor_id)
    except DatabaseConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not doctor:
        raise HTTPException(status_code=401, detail="Doctor account not found.")

    return doctor


def _assert_report_owner(report: dict[str, Any], doctor: dict[str, Any]) -> None:
    owner_id = report.get("doctor_id")
    if owner_id and str(owner_id) != str(doctor["id"]):
        raise HTTPException(status_code=403, detail="You do not have access to this report.")


def _build_patient_context(
    *,
    doctor_id: str | None,
    patient_id: str | None,
    patient_name: str | None,
    patient_age: str | None,
    patient_gender: str | None,
    patient_phone: str | None,
    patient_notes: str | None,
) -> dict[str, Any]:
    if patient_id:
        return get_patient_details(patient_id)

    if not patient_name or not patient_name.strip():
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


def _enrich_report_dict(
    report: dict[str, Any],
    *,
    doctor: dict[str, Any],
    patient: dict[str, Any],
    report_id: str,
) -> dict[str, Any]:
    report["id"] = report_id
    report["report_id"] = report_id
    report["doctor_id"] = doctor.get("id")
    report["doctor_name"] = doctor.get("name") or patient.get("doctor_name") or report.get("doctor_name")
    report["doctor_dept"] = doctor.get("specialization") or report.get("doctor_dept")
    report["clinic_name"] = doctor.get("organization_name") or report.get("clinic_name") or "SehatSaathi Clinic"

    if patient:
        report["patient_id"] = patient.get("id")
        if patient.get("name") is not None:
            report["patient_name"] = patient.get("name")
        if patient.get("age") is not None:
            report["age"] = patient.get("age")
            report["patient_age"] = patient.get("age")
        if patient.get("gender") is not None:
            report["gender"] = patient.get("gender")
            report["patient_gender"] = patient.get("gender")
        if patient.get("phone") is not None:
            report["patient_phone"] = patient.get("phone")
            report["patient_mobile"] = patient.get("phone")
        if patient.get("notes") is not None:
            report["patient_notes"] = patient.get("notes")

    return report


def _ensure_pdf_on_disk(report: dict[str, Any], token: str | None = None) -> tuple[str, str]:
    resolved_token = token or _extract_token_from_pdf_url(report.get("pdf_url")) or uuid4().hex
    pdf_path = _safe_pdf_path(resolved_token)
    if not os.path.exists(pdf_path):
        generate_pdf(report, pdf_path)
    _cache_pdf(pdf_path, token=resolved_token)
    return resolved_token, pdf_path


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/auth/signup")
def signup(payload: SignupRequest):
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
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Signup failed")
        raise HTTPException(status_code=500, detail="Failed to create account.") from exc

    return {
        **doctor,
        "access_token": _create_access_token(doctor),
        "token_type": "bearer",
    }


@app.post("/auth/login")
def login(payload: LoginRequest):
    try:
        doctor = authenticate_doctor(payload.email, payload.password)
    except DatabaseConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except AuthError as exc:
        detail = str(exc)
        status_code = 404 if "No account" in detail else 401
        raise HTTPException(status_code=status_code, detail=detail) from exc
    except Exception as exc:
        logger.exception("Login failed")
        raise HTTPException(status_code=500, detail="Failed to login.") from exc

    return {
        **doctor,
        "access_token": _create_access_token(doctor),
        "token_type": "bearer",
    }


@app.get("/auth/me")
def get_me(current_doctor: dict[str, Any] = Depends(get_current_doctor)):
    return current_doctor


@app.post("/report/pdf")
async def create_report_pdf(
    background_tasks: BackgroundTasks,
    patient_id: str = Form(...),
    audio: UploadFile = File(...),
    current_doctor: dict[str, Any] = Depends(get_current_doctor),
):
    if not audio.filename:
        raise HTTPException(status_code=400, detail="Audio file is required.")

    content = await audio.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty audio file.")
    if len(content) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio file exceeds the 25 MB limit.")

    try:
        patient = await run_in_threadpool(get_patient_details, patient_id)
    except DatabaseConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to fetch patient details")
        raise HTTPException(status_code=500, detail="Failed to fetch patient details.") from exc

    suffix = os.path.splitext(audio.filename)[1] or ".wav"
    audio_path = os.path.join(tempfile.gettempdir(), f"ss_audio_{uuid4().hex}{suffix}")
    with open(audio_path, "wb") as f:
        f.write(content)

    try:
        report = await run_in_threadpool(generate_clinical_report, audio_path, patient)
    except Exception as exc:
        _cleanup_files([audio_path])
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    report_id = str(uuid4())
    report["filename"] = audio.filename
    _enrich_report_dict(report, doctor=current_doctor, patient=patient, report_id=report_id)

    token = uuid4().hex
    pdf_path = _safe_pdf_path(token)

    try:
        await run_in_threadpool(generate_pdf, report, pdf_path)
    except Exception as exc:
        _cleanup_files([audio_path, pdf_path])
        logger.exception("Failed to generate PDF")
        raise HTTPException(status_code=500, detail="Failed to generate PDF.") from exc

    _purge_expired_pdfs()
    _cache_pdf(pdf_path, token=token)

    try:
        await run_in_threadpool(
            create_report_record,
            report,
            patient,
            f"/report/download/{token}",
            current_doctor,
        )
    except Exception as exc:
        _cleanup_files([audio_path])
        raise HTTPException(status_code=500, detail=f"Failed to save report: {exc}") from exc

    background_tasks.add_task(_cleanup_files, [audio_path])

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename="clinical_report.pdf",
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
    current_doctor: dict[str, Any] = Depends(get_current_doctor),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Audio file is required.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty audio file.")
    if len(content) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio file exceeds the 25 MB limit.")

    effective_doctor_id = str(current_doctor["id"])

    patient: dict[str, Any] = {}
    if patient_id or (patient_name and patient_name.strip()):
        try:
            patient = await run_in_threadpool(
                _build_patient_context,
                doctor_id=effective_doctor_id,
                patient_id=patient_id,
                patient_name=patient_name,
                patient_age=patient_age,
                patient_gender=patient_gender,
                patient_phone=patient_phone,
                patient_notes=patient_notes,
            )
        except DatabaseConfigError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except ValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("Failed to resolve patient details")
            raise HTTPException(status_code=500, detail="Failed to resolve patient details.") from exc

    suffix = os.path.splitext(file.filename)[1] or ".wav"
    audio_path = os.path.join(tempfile.gettempdir(), f"ss_audio_{uuid4().hex}{suffix}")
    with open(audio_path, "wb") as f:
        f.write(content)

    try:
        report = await run_in_threadpool(generate_clinical_report, audio_path, patient)
    except Exception as exc:
        _cleanup_files([audio_path])
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    report_id = str(uuid4())
    report["filename"] = file.filename
    _enrich_report_dict(report, doctor=current_doctor, patient=patient, report_id=report_id)

    token = uuid4().hex
    pdf_path = _safe_pdf_path(token)

    try:
        await run_in_threadpool(generate_pdf, report, pdf_path)
    except Exception as exc:
        _cleanup_files([audio_path, pdf_path])
        logger.exception("Failed to generate PDF")
        raise HTTPException(status_code=500, detail="Failed to generate PDF.") from exc

    _purge_expired_pdfs()
    token = _cache_pdf(pdf_path, token=token)
    background_tasks.add_task(_cleanup_files, [audio_path])

    saved = False
    report_record_id = None
    try:
        record = await run_in_threadpool(
            create_report_record,
            report,
            patient,
            f"/report/download/{token}",
            current_doctor,
        )
        report_record_id = record.get("id")
        saved = True
    except Exception as exc:
        logger.exception("Failed to persist report record in MongoDB: %s", exc)

    return {
        "filename": file.filename,
        "transcript": report.get("transcript", ""),
        "report": report,
        "report_id": report.get("report_id"),
        "report_record_id": report_record_id,
        "saved": saved,
        "pdf_download_url": f"/report/download/{token}",
        "patient_id": patient.get("id"),
    }


@app.get("/reports")
def list_reports(
    limit: int = 50,
    current_doctor: dict[str, Any] = Depends(get_current_doctor),
):
    try:
        docs = list_doctor_reports(str(current_doctor["id"]), limit=limit)
    except DatabaseConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"reports": docs}


@app.get("/reports/{report_id}")
def get_report(
    report_id: str,
    current_doctor: dict[str, Any] = Depends(get_current_doctor),
):
    try:
        report = get_report_record(report_id)
    except DatabaseConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    _assert_report_owner(report, current_doctor)
    return report


@app.patch("/reports/{report_id}")
def patch_report(
    report_id: str,
    payload: UpdateReportRequest,
    current_doctor: dict[str, Any] = Depends(get_current_doctor),
):
    updates = payload.model_dump(exclude_unset=True)
    try:
        updated = update_report_record(
            report_id,
            updates,
            doctor_id=str(current_doctor["id"]),
        )
    except DatabaseConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AuthError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Keep doctor metadata present on regenerated PDF
    updated.setdefault("doctor_name", current_doctor.get("name"))
    updated.setdefault("doctor_dept", current_doctor.get("specialization"))
    updated.setdefault("clinic_name", current_doctor.get("organization_name") or "SehatSaathi Clinic")

    token = _extract_token_from_pdf_url(updated.get("pdf_url")) or uuid4().hex
    pdf_path = _safe_pdf_path(token)
    try:
        generate_pdf(updated, pdf_path)
        _cache_pdf(pdf_path, token=token)
    except Exception as exc:
        logger.exception("Failed to regenerate PDF after edit")
        raise HTTPException(status_code=500, detail="Report saved, but PDF regeneration failed.") from exc

    pdf_download_url = updated.get("pdf_url") or f"/report/download/{token}"
    return {
        "report": updated,
        "report_id": updated.get("report_id") or updated.get("id"),
        "pdf_download_url": pdf_download_url,
    }


@app.get("/report/download/{token}")
def download_report(token: str, download: bool = False):
    _purge_expired_pdfs()
    safe_candidate = _safe_pdf_path(token)
    pdf_path = None

    # 1. Check in-memory cache
    entry = _PDF_CACHE.get(token)
    if entry and entry.get("path") and os.path.exists(entry["path"]):
        pdf_path = entry["path"]

    # 2. Check persistent PDF directory
    if not pdf_path and os.path.exists(safe_candidate):
        pdf_path = safe_candidate

    # 3. Exact-match fallback in MongoDB (no substring regex)
    if not pdf_path:
        try:
            from Services.db_service import _get_db, _normalize_doc, _to_object_id

            db = _get_db()
            query_id = _to_object_id(token)
            report = db.reports.find_one({
                "$or": [
                    {"report_id": token},
                    {"pdf_url": f"/report/download/{token}"},
                    {"_id": query_id},
                ]
            })
            if report:
                normalized = _normalize_doc(report)
                generate_pdf(normalized, safe_candidate)
                pdf_path = safe_candidate
                _cache_pdf(pdf_path, token=token)
        except Exception as exc:
            logger.debug("PDF fallback lookup failed for token %s: %s", token, exc)

    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF not found or expired.")

    disposition = "attachment" if download else "inline"
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename="clinical_report.pdf",
        content_disposition_type=disposition,
    )


@app.get("/whatsapp/status")
def whatsapp_status(current_doctor: dict[str, Any] = Depends(get_current_doctor)):
    return get_whatsapp_status(str(current_doctor["id"]))


@app.post("/whatsapp/connect")
def whatsapp_connect(current_doctor: dict[str, Any] = Depends(get_current_doctor)):
    try:
        return connect_whatsapp_session(str(current_doctor["id"]))
    except WhatsAppConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/whatsapp/pairing-code")
def whatsapp_pairing_code(
    payload: PairingCodeRequest,
    current_doctor: dict[str, Any] = Depends(get_current_doctor),
):
    try:
        return request_whatsapp_pairing_code(str(current_doctor["id"]), payload.phone)
    except WhatsAppValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except WhatsAppConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/whatsapp/logout")
def whatsapp_logout(current_doctor: dict[str, Any] = Depends(get_current_doctor)):
    try:
        return logout_whatsapp_session(str(current_doctor["id"]))
    except WhatsAppConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/reports/{report_id}/send-whatsapp")
def send_report_whatsapp(
    report_id: str,
    request: Request,
    payload: SendWhatsAppRequest | None = Body(default=None),
    current_doctor: dict[str, Any] = Depends(get_current_doctor),
):
    if not is_whatsapp_enabled():
        raise HTTPException(status_code=503, detail="WhatsApp gateway is not configured.")

    try:
        report = get_report_record(report_id)
    except DatabaseConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    _assert_report_owner(report, current_doctor)

    token, pdf_path = _ensure_pdf_on_disk(report)
    pdf_url = _absolute_url(request, report.get("pdf_url") or f"/report/download/{token}")
    phone_override = payload.phone.strip() if payload and payload.phone else None

    try:
        result = send_report_whatsapp_message(
            report,
            pdf_path=pdf_path,
            pdf_url=pdf_url,
            doctor_id=str(current_doctor["id"]),
            phone_override=phone_override,
        )
    except WhatsAppValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except WhatsAppNotConnectedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except WhatsAppConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error sending WhatsApp report")
        raise HTTPException(status_code=500, detail="Failed to send WhatsApp message.") from exc

    return {
        "status": "sent",
        "report_id": report_id,
        "message_id": result.get("message_id"),
        "to": result.get("to"),
        "delivery": result.get("delivery"),
    }


if os.path.exists(DIST_DIR):
    app.mount("/", StaticFiles(directory=DIST_DIR, html=True), name="static")
