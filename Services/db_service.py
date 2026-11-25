import hmac
import logging
import os
from datetime import datetime, timezone
from hashlib import pbkdf2_hmac
from secrets import token_hex
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from dotenv import load_dotenv
from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.errors import ConfigurationError, ConnectionFailure, ServerSelectionTimeoutError

load_dotenv()

logger = logging.getLogger("sehatsaathi.db")


class DatabaseConfigError(RuntimeError):
    pass


class NotFoundError(ValueError):
    pass


class ConflictError(ValueError):
    pass


class AuthError(ValueError):
    pass


class ValidationError(ValueError):
    pass


# ---------------------------------------------------------------------------
# Connection (lazy singleton)
# ---------------------------------------------------------------------------

_client: MongoClient | None = None
_db = None
_indexes_ready = False


def _ensure_indexes(db) -> None:
    global _indexes_ready
    if _indexes_ready:
        return
    try:
        db.doctors.create_index([("email", ASCENDING)], unique=True, name="uniq_doctor_email")
    except Exception as exc:
        logger.warning("Could not create unique index on doctors.email: %s", exc)
    try:
        db.patients.create_index([("doctor_id", ASCENDING)], name="idx_patients_doctor")
        db.reports.create_index([("report_id", ASCENDING)], name="idx_reports_report_id")
        db.reports.create_index(
            [("doctor_id", ASCENDING), ("created_at", DESCENDING)],
            name="idx_reports_doctor_created",
        )
    except Exception as exc:
        logger.warning("Could not create secondary indexes: %s", exc)
    _indexes_ready = True


def _get_db():
    global _client, _db

    if _db is not None:
        return _db

    mongo_uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGODB_DB", "sehatsaathi")

    if not mongo_uri:
        raise DatabaseConfigError(
            "MONGODB_URI must be configured in the environment."
        )

    client = None
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        _client = client
        _db = _client[db_name]
        _ensure_indexes(_db)
        return _db
    except (ConnectionFailure, ServerSelectionTimeoutError, ConfigurationError) as exc:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass
        _client = None
        _db = None
        raise DatabaseConfigError(f"MongoDB connection failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_object_id(id_str: str) -> ObjectId | str:
    """Return an ObjectId if the string is a valid one, else return it as-is."""
    try:
        return ObjectId(id_str)
    except (InvalidId, TypeError):
        return id_str


def _doctor_id_variants(doctor_id: str | ObjectId | None) -> list[Any]:
    if not doctor_id:
        return []
    as_str = str(doctor_id)
    as_oid = _to_object_id(as_str)
    if isinstance(as_oid, ObjectId):
        return [as_str, as_oid]
    return [as_str]


def _serialize_value(value):
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, dict):
        return {key: _serialize_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    return value


def _normalize_doc(doc: dict) -> dict:
    """Convert _id -> id (string) so callers get a consistent 'id' field."""
    if doc and "_id" in doc:
        doc = dict(doc)
        doc["id"] = str(doc.pop("_id"))
    return _serialize_value(doc)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or token_hex(16)
    password_hash = pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120000,
    ).hex()
    return salt, password_hash


def _public_doctor_profile(doctor: dict[str, Any]) -> dict[str, Any]:
    doctor = _normalize_doc(doctor)
    doctor.pop("password_hash", None)
    doctor.pop("password_salt", None)
    return {
        "id": doctor.get("id"),
        "name": doctor.get("name"),
        "email": doctor.get("email"),
        "specialization": doctor.get("specialization"),
        "organization_name": doctor.get("organization_name"),
    }


def _normalize_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item or "").strip()]
    if isinstance(value, str):
        return [line.strip() for line in value.splitlines() if line.strip()]
    text = str(value).strip()
    return [text] if text else []


def _parse_age(age_value: Any) -> int | None:
    if age_value is None:
        return None
    if isinstance(age_value, bool):
        raise ValidationError("Patient age must be a whole number between 0 and 150.")
    if isinstance(age_value, int):
        age = age_value
    else:
        raw = str(age_value).strip()
        if not raw:
            return None
        try:
            age = int(raw)
        except ValueError as exc:
            raise ValidationError("Patient age must be a whole number between 0 and 150.") from exc
    if age < 0 or age > 150:
        raise ValidationError("Patient age must be a whole number between 0 and 150.")
    return age


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_doctor_by_id(doctor_id: str) -> dict[str, Any] | None:
    if not doctor_id:
        return None
    db = _get_db()
    doc_oid = _to_object_id(str(doctor_id))
    doctor = db.doctors.find_one({"_id": doc_oid}) or db.doctors.find_one({"id": str(doctor_id)})
    if not doctor:
        return None
    return _public_doctor_profile(doctor)


def get_patient_details(patient_id: str) -> dict[str, Any]:
    """
    Fetch a patient document by id.

    Looks up the `patients` collection first by ObjectId, then by the
    string field `id`. Joins the matching doctor from `doctors`.
    """
    db = _get_db()

    query_id = _to_object_id(patient_id)
    patient = db.patients.find_one({"_id": query_id})

    if patient is None:
        patient = db.patients.find_one({"id": patient_id})

    if not patient:
        raise NotFoundError("Patient not found.")

    patient = _normalize_doc(patient)

    doctor_id = patient.get("doctor_id")
    doctor: dict = {}

    if doctor_id:
        doc_oid = _to_object_id(str(doctor_id))
        doctor = db.doctors.find_one({"_id": doc_oid}) or {}
        if not doctor:
            doctor = db.doctors.find_one({"id": str(doctor_id)}) or {}
        if doctor:
            doctor = _public_doctor_profile(doctor)

    patient["doctor_name"] = doctor.get("name")
    patient["doctor"] = doctor if doctor else {}

    return patient


def create_doctor_account(
    name: str,
    email: str,
    password: str,
    specialization: str | None = None,
    organization_name: str | None = None,
) -> dict[str, Any]:
    db = _get_db()
    normalized_email = email.strip().lower()
    cleaned_name = name.strip()
    if not cleaned_name:
        raise ValidationError("Doctor name is required.")
    if len(password or "") < 6:
        raise ValidationError("Password must be at least 6 characters long.")

    existing = db.doctors.find_one({"email": normalized_email})
    if existing:
        raise ConflictError("An account with this email already exists.")

    password_salt, password_hash = _hash_password(password)
    payload = {
        "name": cleaned_name,
        "email": normalized_email,
        "specialization": specialization.strip() if specialization else None,
        "organization_name": organization_name.strip() if organization_name else None,
        "password_salt": password_salt,
        "password_hash": password_hash,
        "created_at": _utcnow_iso(),
    }

    result = db.doctors.insert_one(payload)
    payload["_id"] = result.inserted_id
    return _public_doctor_profile(payload)


def authenticate_doctor(email: str, password: str) -> dict[str, Any]:
    db = _get_db()
    normalized_email = email.strip().lower()
    doctor = db.doctors.find_one({"email": normalized_email})

    if not doctor:
        raise AuthError("No account found with this email.")

    salt = doctor.get("password_salt")
    expected_hash = doctor.get("password_hash")
    if not salt or not expected_hash:
        raise AuthError("Account credentials are invalid.")

    _, password_hash = _hash_password(password, salt=salt)

    if not hmac.compare_digest(password_hash, expected_hash):
        raise AuthError("Incorrect password.")

    return _public_doctor_profile(doctor)


def upsert_patient_record(
    doctor_id: str | None,
    patient_data: dict[str, Any],
) -> dict[str, Any]:
    db = _get_db()

    patient_name = (patient_data.get("name") or "").strip()
    if not patient_name:
        return {}

    phone = (patient_data.get("phone") or "").strip() or None
    age = _parse_age(patient_data.get("age"))
    gender = (patient_data.get("gender") or "").strip() or None
    notes = (patient_data.get("notes") or "").strip() or None

    doctor_id_str = str(doctor_id) if doctor_id else None
    doctor_variants = _doctor_id_variants(doctor_id_str)

    lookup_query: dict[str, Any] = {"name": patient_name}
    if doctor_variants:
        lookup_query["doctor_id"] = {"$in": doctor_variants}
    else:
        lookup_query["doctor_id"] = None

    if phone:
        lookup_query["phone"] = phone
    else:
        lookup_query["phone"] = None

    update_payload = {
        "doctor_id": doctor_id_str,
        "name": patient_name,
        "age": age,
        "gender": gender,
        "phone": phone,
        "notes": notes,
        "updated_at": _utcnow_iso(),
    }

    existing = db.patients.find_one(lookup_query)
    if existing:
        db.patients.update_one({"_id": existing["_id"]}, {"$set": update_payload})
        existing.update(update_payload)
        patient = _normalize_doc(existing)
    else:
        payload = {
            **update_payload,
            "created_at": _utcnow_iso(),
        }
        result = db.patients.insert_one(payload)
        payload["_id"] = result.inserted_id
        patient = _normalize_doc(payload)

    if doctor_id_str:
        doctor = get_doctor_by_id(doctor_id_str)
        if doctor:
            patient["doctor_name"] = doctor.get("name")
            patient["doctor"] = doctor

    return patient


def create_report_record(
    report: dict[str, Any],
    patient: dict[str, Any] | None = None,
    pdf_url: str | None = None,
    doctor: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Insert a clinical report document into the `reports` collection.
    Returns the normalized payload dict (with 'id').
    """
    db = _get_db()
    patient = patient or {}
    doctor = doctor or patient.get("doctor") or {}

    doctor_id = (
        doctor.get("id")
        or report.get("doctor_id")
        or patient.get("doctor_id")
    )
    doctor_name = (
        doctor.get("name")
        or report.get("doctor_name")
        or patient.get("doctor_name")
    )
    doctor_dept = (
        doctor.get("specialization")
        or report.get("doctor_dept")
    )
    clinic_name = (
        doctor.get("organization_name")
        or report.get("clinic_name")
        or "SehatSaathi Clinic"
    )

    patient_age = patient.get("age")
    if patient_age is None:
        patient_age = report.get("patient_age")
    if patient_age is None:
        patient_age = report.get("age")

    now = _utcnow_iso()
    payload = {
        "report_id": report.get("report_id") or report.get("id"),
        "filename": report.get("filename"),
        "doctor_id": str(doctor_id) if doctor_id else None,
        "doctor_name": doctor_name,
        "doctor_dept": doctor_dept,
        "clinic_name": clinic_name,
        "clinic_address": report.get("clinic_address"),
        "visit_type": report.get("visit_type") or "Consultation",
        "patient_id": patient.get("id") or report.get("patient_id"),
        "patient_name": patient.get("name") or report.get("patient_name"),
        "patient_age": patient_age,
        "patient_gender": patient.get("gender") or report.get("patient_gender") or report.get("gender"),
        "patient_phone": patient.get("phone") or report.get("patient_phone") or report.get("patient_mobile"),
        "patient_notes": patient.get("notes") or report.get("patient_notes"),
        "transcript": report.get("transcript") or "",
        "symptoms": _normalize_str_list(report.get("symptoms")),
        "diagnosis": str(report.get("diagnosis") or "").strip(),
        "medications": _normalize_str_list(report.get("medications")),
        "dosage": _normalize_str_list(report.get("dosage")),
        "precautions": _normalize_str_list(report.get("precautions")),
        "follow_up": str(report.get("follow_up") or "").strip(),
        "doctor_notes": str(report.get("doctor_notes") or "").strip(),
        "pdf_url": pdf_url,
        "created_at": now,
        "updated_at": now,
    }

    result = db.reports.insert_one(payload)
    payload["_id"] = result.inserted_id
    return _normalize_doc(payload)


def get_report_record(report_id: str) -> dict[str, Any]:
    db = _get_db()

    report = db.reports.find_one({"report_id": report_id})
    if report is None:
        query_id = _to_object_id(report_id)
        report = db.reports.find_one({"_id": query_id})

    if not report:
        raise NotFoundError("Report not found.")

    return _normalize_doc(report)


def list_doctor_reports(doctor_id: str, limit: int = 50) -> list[dict[str, Any]]:
    db = _get_db()
    variants = _doctor_id_variants(doctor_id)
    if not variants:
        return []
    cursor = (
        db.reports.find({"doctor_id": {"$in": variants}})
        .sort("created_at", DESCENDING)
        .limit(max(1, min(limit, 200)))
    )
    return [_normalize_doc(doc) for doc in cursor]


def update_report_record(
    report_id: str,
    updates: dict[str, Any],
    doctor_id: str | None = None,
) -> dict[str, Any]:
    db = _get_db()

    report = db.reports.find_one({"report_id": report_id})
    if report is None:
        query_id = _to_object_id(report_id)
        report = db.reports.find_one({"_id": query_id})

    if not report:
        raise NotFoundError("Report not found.")

    if doctor_id is not None:
        doc_owner = report.get("doctor_id")
        if doc_owner and str(doc_owner) != str(doctor_id):
            raise AuthError("You do not have permission to edit this report.")

    list_fields = {"symptoms", "medications", "dosage", "precautions"}
    str_fields = {
        "diagnosis",
        "follow_up",
        "doctor_notes",
        "patient_name",
        "patient_gender",
        "patient_phone",
        "patient_notes",
        "visit_type",
    }

    set_payload: dict[str, Any] = {"updated_at": _utcnow_iso()}

    for key, value in updates.items():
        if value is None:
            continue
        if key in list_fields:
            set_payload[key] = _normalize_str_list(value)
        elif key in str_fields:
            set_payload[key] = str(value).strip()
        elif key == "patient_age":
            set_payload["patient_age"] = _parse_age(value)

    db.reports.update_one({"_id": report["_id"]}, {"$set": set_payload})
    refreshed = db.reports.find_one({"_id": report["_id"]})
    return _normalize_doc(refreshed)
