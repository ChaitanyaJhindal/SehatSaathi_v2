import atexit
import base64
import logging
import os
import re
import shutil
import subprocess
import threading
import time
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("sehatsaathi.whatsapp")

_SERVICE_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_SERVICE_DIR)
_BRIDGE_DIR = os.path.join(_SERVICE_DIR, "wa_bridge")
_BRIDGE_SCRIPT = os.path.join(_BRIDGE_DIR, "server.mjs")
_SESSIONS_DIR = os.path.join(_ROOT_DIR, "output", "wa_sessions")
_LOG_DIR = os.path.join(_ROOT_DIR, "output")

_bridge_lock = threading.Lock()
_bridge_proc: subprocess.Popen | None = None
_atexit_registered = False


class WhatsAppConfigError(RuntimeError):
    """Local WhatsApp bridge configuration or startup error (HTTP 503)."""


class WhatsAppValidationError(ValueError):
    """Invalid phone number or missing target recipient (HTTP 400)."""


class WhatsAppNotConnectedError(RuntimeError):
    """Doctor's WhatsApp session is not linked/ready yet (HTTP 409)."""


def _bridge_port() -> int:
    try:
        return int(os.getenv("WA_BRIDGE_PORT", "2785"))
    except ValueError:
        return 2785


def _bridge_base_url() -> str:
    custom = os.getenv("WA_BRIDGE_URL", "").strip().rstrip("/")
    if custom:
        return custom
    return f"http://127.0.0.1:{_bridge_port()}"


def _get_default_country_code() -> str:
    digits = re.sub(r"\D", "", os.getenv("DEFAULT_PHONE_COUNTRY_CODE", "91"))
    return digits or "91"


def is_whatsapp_enabled() -> bool:
    return os.path.exists(_BRIDGE_SCRIPT)


def session_name_for_doctor(doctor_id: str | None = None) -> str:
    override = os.getenv("WA_SESSION_NAME", "").strip()
    if override and not doctor_id:
        clean = re.sub(r"[^a-zA-Z0-9_-]", "-", override).strip("-")
        if len(clean) >= 3:
            return clean[:50]

    if doctor_id:
        clean_id = re.sub(r"[^a-zA-Z0-9]", "", str(doctor_id))[:24]
        if clean_id:
            return f"sehatsaathi-{clean_id}"

    return "sehatsaathi-main"


def format_chat_id(phone_number: str) -> str:
    raw = str(phone_number or "").strip()
    if not raw:
        raise WhatsAppValidationError("Patient phone number is required.")

    if "@" in raw:
        if re.fullmatch(r"[^\s@]+@[^\s@]+", raw):
            return raw
        raise WhatsAppValidationError("Invalid WhatsApp chat ID format.")

    digits = re.sub(r"\D", "", raw)
    if not digits:
        raise WhatsAppValidationError("Invalid patient phone number.")

    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]

    if len(digits) == 10:
        digits = f"{_get_default_country_code()}{digits}"

    if len(digits) < 10 or len(digits) > 15:
        raise WhatsAppValidationError("Phone number must contain 10 to 15 digits.")

    return f"{digits}@c.us"


def _format_pairing_phone(phone_number: str) -> str:
    return format_chat_id(phone_number).split("@")[0]


def _bridge_healthy() -> bool:
    try:
        resp = httpx.get(f"{_bridge_base_url()}/health", timeout=1.5)
        return resp.status_code == 200
    except Exception:
        return False


def stop_whatsapp_bridge() -> None:
    global _bridge_proc
    with _bridge_lock:
        proc = _bridge_proc
        _bridge_proc = None
    if proc is not None and proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=4)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


def _ensure_bridge_running() -> None:
    global _bridge_proc, _atexit_registered

    if os.getenv("WA_BRIDGE_URL", "").strip():
        return

    if _bridge_healthy():
        return

    with _bridge_lock:
        if _bridge_healthy():
            return

        node_bin = shutil.which("node")
        if not node_bin:
            raise WhatsAppConfigError(
                "Node.js is required on PATH to run the built-in WhatsApp service."
            )
        if not os.path.exists(_BRIDGE_SCRIPT):
            raise WhatsAppConfigError("Built-in WhatsApp bridge script is missing.")
        if not os.path.exists(os.path.join(_BRIDGE_DIR, "node_modules")):
            raise WhatsAppConfigError(
                "WhatsApp bridge dependencies are not installed. Run: npm install --prefix Services/wa_bridge"
            )

        if _bridge_proc is not None and _bridge_proc.poll() is not None:
            _bridge_proc = None

        if _bridge_proc is None:
            os.makedirs(_SESSIONS_DIR, exist_ok=True)
            os.makedirs(_LOG_DIR, exist_ok=True)
            log_path = os.path.join(_LOG_DIR, "wa_bridge.log")
            env = {
                **os.environ,
                "WA_BRIDGE_PORT": str(_bridge_port()),
                "WA_SESSIONS_DIR": _SESSIONS_DIR,
            }
            kwargs: dict[str, Any] = {
                "cwd": _BRIDGE_DIR,
                "env": env,
            }
            if os.name == "nt":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            log_file = open(log_path, "ab")
            try:
                kwargs["stdout"] = log_file
                kwargs["stderr"] = subprocess.STDOUT
                _bridge_proc = subprocess.Popen([node_bin, _BRIDGE_SCRIPT], **kwargs)
            finally:
                log_file.close()

            if not _atexit_registered:
                atexit.register(stop_whatsapp_bridge)
                _atexit_registered = True

    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline:
        if _bridge_healthy():
            return
        if _bridge_proc is not None and _bridge_proc.poll() is not None:
            raise WhatsAppConfigError(
                "Built-in WhatsApp bridge exited during startup. Check output/wa_bridge.log."
            )
        time.sleep(0.25)

    raise WhatsAppConfigError("Timed out waiting for the built-in WhatsApp bridge to start.")


def _extract_error_detail(response: httpx.Response) -> str:
    try:
        data = response.json()
        if isinstance(data, dict):
            msg = data.get("message") or data.get("error") or data.get("detail")
            if msg:
                return str(msg)
    except Exception:
        pass
    return response.text or f"HTTP {response.status_code}"


def _bridge_request(
    method: str,
    path: str,
    *,
    json_body: dict[str, Any] | None = None,
    timeout: float = 25.0,
) -> httpx.Response:
    _ensure_bridge_running()
    url = f"{_bridge_base_url()}{path}"
    try:
        with httpx.Client(timeout=timeout) as client:
            return client.request(method, url, json=json_body)
    except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as exc:
        raise WhatsAppConfigError(f"WhatsApp service communication failed: {exc}") from exc


def get_whatsapp_status(doctor_id: str | None = None) -> dict[str, Any]:
    session_name = session_name_for_doctor(doctor_id)
    try:
        resp = _bridge_request("GET", f"/sessions/{session_name}/status", timeout=10.0)
        if resp.status_code >= 400:
            raise WhatsAppConfigError(_extract_error_detail(resp))
        return resp.json()
    except WhatsAppConfigError as exc:
        return {
            "gateway_reachable": False,
            "configured": False,
            "session_id": session_name,
            "session_name": session_name,
            "status": "service_error",
            "connected": False,
            "phone": None,
            "push_name": None,
            "qr_code": None,
            "last_error": str(exc),
        }


def connect_whatsapp_session(doctor_id: str | None = None) -> dict[str, Any]:
    session_name = session_name_for_doctor(doctor_id)
    resp = _bridge_request("POST", f"/sessions/{session_name}/connect", timeout=30.0)
    if resp.status_code >= 400:
        raise WhatsAppConfigError(_extract_error_detail(resp))
    return resp.json()


def request_whatsapp_pairing_code(
    doctor_id: str | None,
    phone_number: str,
) -> dict[str, Any]:
    formatted_phone = _format_pairing_phone(phone_number)
    session_name = session_name_for_doctor(doctor_id)
    resp = _bridge_request(
        "POST",
        f"/sessions/{session_name}/pairing-code",
        json_body={"phoneNumber": formatted_phone},
        timeout=30.0,
    )
    if resp.status_code == 400:
        raise WhatsAppValidationError(_extract_error_detail(resp))
    if resp.status_code >= 400:
        raise WhatsAppConfigError(_extract_error_detail(resp))
    return resp.json()


def logout_whatsapp_session(doctor_id: str | None = None) -> dict[str, Any]:
    session_name = session_name_for_doctor(doctor_id)
    resp = _bridge_request("POST", f"/sessions/{session_name}/logout", timeout=20.0)
    if resp.status_code >= 400:
        raise WhatsAppConfigError(_extract_error_detail(resp))
    return resp.json()


def send_report_whatsapp_message(
    report: dict[str, Any],
    pdf_path: str | None = None,
    pdf_url: str | None = None,
    doctor_id: str | None = None,
    phone_override: str | None = None,
) -> dict[str, Any]:
    phone_number = phone_override or report.get("patient_phone") or report.get("patient_mobile")
    chat_id = format_chat_id(phone_number)

    resolved_doctor_id = doctor_id or report.get("doctor_id")
    session_name = session_name_for_doctor(str(resolved_doctor_id) if resolved_doctor_id else None)

    patient_name = report.get("patient_name") or "Patient"
    diagnosis = str(report.get("diagnosis") or "").strip()

    caption_lines = [f"Hello {patient_name}, your SehatSaathi clinical consultation report is ready."]
    if diagnosis:
        caption_lines.append(f"Diagnosis: {diagnosis}")
    if pdf_url and "localhost" not in pdf_url and "127.0.0.1" not in pdf_url:
        caption_lines.append(f"Download link: {pdf_url}")
    caption = "\n".join(caption_lines)

    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            b64_pdf = base64.b64encode(f.read()).decode("ascii")
        safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(patient_name)).strip("_") or "patient"
        filename = f"SehatSaathi_Report_{safe_name}.pdf"

        resp = _bridge_request(
            "POST",
            f"/sessions/{session_name}/send-document",
            json_body={
                "chatId": chat_id,
                "base64": b64_pdf,
                "mimetype": "application/pdf",
                "filename": filename,
                "caption": caption,
            },
            timeout=35.0,
        )
        delivery = "document"
    else:
        resp = _bridge_request(
            "POST",
            f"/sessions/{session_name}/send-text",
            json_body={
                "chatId": chat_id,
                "text": caption,
            },
            timeout=35.0,
        )
        delivery = "text"

    if resp.status_code == 409:
        raise WhatsAppNotConnectedError(
            "WhatsApp is not connected. Open 'Connect WhatsApp' and scan the QR code first."
        )
    if resp.status_code == 400:
        raise WhatsAppValidationError(_extract_error_detail(resp))
    if resp.status_code >= 400:
        raise WhatsAppConfigError(_extract_error_detail(resp))

    data = resp.json() if resp.content else {}
    return {
        "message_id": data.get("id") or data.get("messageId"),
        "to": data.get("to") or chat_id,
        "session_id": session_name,
        "delivery": delivery,
    }
