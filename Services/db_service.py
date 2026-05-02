import os
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


def _normalize_doc(doc: dict) -> dict:
    """Convert _id → id (string) so callers get a consistent 'id' field."""
    if doc and "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc


# ---------------------------------------------------------------------------
# Public API (same signatures as the old Supabase version)
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
        "transcript": report.get("transcript"),
        "symptoms": report.get("symptoms", []),
        "diagnosis": report.get("diagnosis"),
        "medications": report.get("medications", []),
        "dosage": report.get("dosage", []),
        "precautions": report.get("precautions", []),
        "doctor_notes": report.get("doctor_notes"),
        "pdf_url": pdf_url,
    }

    result = db.reports.insert_one(payload)
    payload["id"] = str(result.inserted_id)
    return payload
