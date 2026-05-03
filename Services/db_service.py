import os
from datetime import datetime, timezone
from hashlib import pbkdf2_hmac
from secrets import token_hex
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConfigurationError, ConnectionFailure, ServerSelectionTimeoutError

load_dotenv()


class DatabaseConfigError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Connection (lazy singleton)
# ---------------------------------------------------------------------------

_client: MongoClient | None = None
_db = None


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

    try:
        _client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        # Trigger immediate connection validation
        _client.admin.command("ping")
        _db = _client[db_name]
        return _db
    except (ConnectionFailure, ServerSelectionTimeoutError, ConfigurationError) as exc:
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


def _serialize_value(value):
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, dict):
        return {key: _serialize_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    return value


def _normalize_doc(doc: dict) -> dict:
    """Convert _id → id (string) so callers get a consistent 'id' field."""
    if doc and "_id" in doc:
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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_patient_details(patient_id: str) -> dict[str, Any]:
    """
    Fetch a patient document by id.

    Looks up the `patients` collection first by ObjectId, then by the
    string field ``id`` (for seeds that store it that way).  Joins the
    matching doctor from the `doctors` collection.
    """
    db = _get_db()

    # Try ObjectId match on _id, fall back to a plain string id field
    query_id = _to_object_id(patient_id)
    patient = db.patients.find_one({"_id": query_id})

    if patient is None:
        # Maybe the collection stores id as a separate string field
        patient = db.patients.find_one({"id": patient_id})

    if not patient:
        raise ValueError("Patient not found.")

    patient = _normalize_doc(patient)

    # --- join doctor ---
    doctor_id = patient.get("doctor_id")
    doctor: dict = {}

    if doctor_id:
        doc_oid = _to_object_id(str(doctor_id))
        doctor = db.doctors.find_one({"_id": doc_oid}) or {}
        if not doctor:
            doctor = db.doctors.find_one({"id": str(doctor_id)}) or {}
        if doctor:
            doctor = _normalize_doc(doctor)

    patient["doctor_name"] = doctor.get("name")
    patient["doctor"] = {
        "id": doctor.get("id", ""),
        "name": doctor.get("name"),
        "specialization": doctor.get("specialization"),
        "email": doctor.get("email"),
    } if doctor else {}

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

    existing = db.doctors.find_one({"email": normalized_email})
    if existing:
        raise ValueError("An account with this email already exists.")

    password_salt, password_hash = _hash_password(password)
    payload = {
        "name": name.strip(),
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
        raise ValueError("No account found with this email.")

    salt = doctor.get("password_salt")
    expected_hash = doctor.get("password_hash")
    _, password_hash = _hash_password(password, salt=salt)

    if password_hash != expected_hash:
        raise ValueError("Incorrect password.")

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
    age_value = patient_data.get("age")
    age = int(age_value) if age_value not in (None, "") else None
    gender = (patient_data.get("gender") or "").strip() or None
    notes = (patient_data.get("notes") or "").strip() or None

    doctor_ref = _to_object_id(doctor_id) if doctor_id else None
    lookup_query = {"doctor_id": doctor_ref, "name": patient_name}
    if phone:
        lookup_query["phone"] = phone

    update_payload = {
        "doctor_id": doctor_ref,
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

    if doctor_id:
        doctor_ref = _to_object_id(doctor_id)
        doctor = db.doctors.find_one({"_id": doctor_ref}) or db.doctors.find_one({"id": str(doctor_id)}) or {}
        if doctor:
            doctor = _public_doctor_profile(doctor)
            patient["doctor_name"] = doctor.get("name")
            patient["doctor"] = doctor

    return patient


def create_report_record(
    report: dict[str, Any],
    patient: dict[str, Any],
    pdf_url: str | None = None,
) -> dict[str, Any]:
    """
    Insert a clinical report document into the `reports` collection.

    Returns the payload dict (with the new MongoDB _id added as 'id').
    """
    db = _get_db()

    payload = {
        "report_id": report.get("id"),
        "doctor_id": patient.get("doctor_id"),
        "patient_id": patient.get("id"),
        "patient_name": patient.get("name") or report.get("patient_name"),
        "patient_age": patient.get("age") if patient.get("age") is not None else report.get("age"),
        "patient_gender": patient.get("gender") or report.get("gender"),
        "patient_phone": patient.get("phone"),
        "patient_notes": patient.get("notes"),
        "transcript": report.get("transcript"),
        "symptoms": report.get("symptoms", []),
        "diagnosis": report.get("diagnosis"),
        "medications": report.get("medications", []),
        "dosage": report.get("dosage", []),
        "precautions": report.get("precautions", []),
        "doctor_notes": report.get("doctor_notes"),
        "pdf_url": pdf_url,
        "created_at": _utcnow_iso(),
    }

    result = db.reports.insert_one(payload)
    payload["id"] = str(result.inserted_id)
    return payload
