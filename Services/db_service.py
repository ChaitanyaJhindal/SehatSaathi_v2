import json
import os
from typing import Any
from urllib import error, parse, request

from dotenv import load_dotenv

load_dotenv()


class DatabaseConfigError(RuntimeError):
    pass


def _supabase_request(path: str, query: dict[str, str]) -> list[dict[str, Any]]:
    supabase_url = os.getenv("SUPABASE_URL")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not service_role_key:
        raise DatabaseConfigError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured."
        )

    encoded_query = parse.urlencode(query)
    url = f"{supabase_url.rstrip('/')}/rest/v1/{path}?{encoded_query}"

    req = request.Request(
        url,
        headers={
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Accept": "application/json",
        },
    )

    try:
        with request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Supabase request failed: {exc.code} {message}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Supabase connection failed: {exc.reason}") from exc


def get_patient_details(patient_id: str) -> dict[str, Any]:
    rows = _supabase_request(
        "patients",
        {
            "id": f"eq.{patient_id}",
            "select": "id,name,age,gender,doctor_id",
            "limit": "1",
        },
    )

    if not rows:
        raise ValueError("Patient not found.")

    return rows[0]
