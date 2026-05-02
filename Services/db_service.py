import json
import os
from typing import Any
from urllib import error, parse, request

from dotenv import load_dotenv

load_dotenv()


class DatabaseConfigError(RuntimeError):
    pass


def _supabase_request(
    path: str,
    query: dict[str, str] | None = None,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    prefer: str | None = None,
) -> Any:
    supabase_url = os.getenv("SUPABASE_URL")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not service_role_key:
        raise DatabaseConfigError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured."
        )

        base_url = supabase_url.rstrip("/")
        if base_url.endswith("/rest/v1"):
            base_url = base_url[: -len("/rest/v1")]

        encoded_query = parse.urlencode(query or {})
        url = f"{base_url}/rest/v1/{path}"
    if encoded_query:
        url = f"{url}?{encoded_query}"

    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Accept": "application/json",
    }
    data = None

    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")

    if prefer:
        headers["Prefer"] = prefer

    req = request.Request(url, data=data, headers=headers, method=method)

    try:
        with request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        if exc.code == 404 and "PGRST125" in message:
            raise RuntimeError(
                "Supabase table endpoint not found. Run the latest schema.sql in the Supabase SQL Editor first."
            ) from exc
        raise RuntimeError(f"Supabase request failed: {exc.code} {message}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Supabase connection failed: {exc.reason}") from exc


def get_patient_details(patient_id: str) -> dict[str, Any]:
    rows = _supabase_request(
        "patients",
        {
            "id": f"eq.{patient_id}",
            "select": "id,name,age,gender,doctor_id,doctor:doctors(id,name,specialization,email)",
            "limit": "1",
        },
    )

    if not rows:
        raise ValueError("Patient not found.")

    patient = rows[0]
    doctor = patient.get("doctor") or {}
    patient["doctor_name"] = doctor.get("name")
    return patient


def create_report_record(report: dict[str, Any], patient: dict[str, Any], pdf_url: str | None = None) -> dict[str, Any]:
    payload = {
        "id": report.get("id"),
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

    created = _supabase_request(
        "reports",
        method="POST",
        payload=payload,
        prefer="return=representation",
    )

    if isinstance(created, list) and created:
        return created[0]
    return payload
