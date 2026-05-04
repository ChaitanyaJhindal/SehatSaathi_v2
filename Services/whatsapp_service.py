import json
import os
from typing import Any

from dotenv import load_dotenv

try:
    from twilio.base.exceptions import TwilioRestException
    from twilio.rest import Client
except ImportError:  # pragma: no cover - optional dependency path
    Client = None
    TwilioRestException = Exception

load_dotenv()


class WhatsAppConfigError(RuntimeError):
    pass


def is_whatsapp_enabled() -> bool:
    return bool(
        os.getenv("TWILIO_ACCOUNT_SID")
        and os.getenv("TWILIO_AUTH_TOKEN")
        and os.getenv("TWILIO_WHATSAPP_FROM")
    )


def _format_whatsapp_number(phone_number: str) -> str:
    value = str(phone_number or "").strip()
    if value.startswith("whatsapp:"):
        return value

    normalized = "".join(ch for ch in value if ch.isdigit() or ch == "+").strip()
    if not normalized:
        raise WhatsAppConfigError("Patient phone number is missing.")
    if normalized.startswith("00"):
        normalized = f"+{normalized[2:]}"
    elif not normalized.startswith("+"):
        normalized = f"+{normalized}"
    return f"whatsapp:{normalized}"


def _get_client() -> Client:
    if Client is None:
        raise WhatsAppConfigError("Twilio SDK is not installed.")

    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")

    if not account_sid or not auth_token:
        raise WhatsAppConfigError("Twilio WhatsApp credentials are not configured.")

    return Client(account_sid, auth_token)


def send_report_whatsapp_message(report: dict[str, Any], pdf_url: str) -> dict[str, str]:
    if not is_whatsapp_enabled():
        raise WhatsAppConfigError("Twilio WhatsApp service is not configured.")

    phone_number = report.get("patient_phone")
    if not phone_number:
        raise WhatsAppConfigError("Patient phone number is missing on the saved report.")

    from_number = os.getenv("TWILIO_WHATSAPP_FROM")
    content_sid = os.getenv("TWILIO_WHATSAPP_CONTENT_SID")
    patient_name = report.get("patient_name") or "Patient"

    payload: dict[str, Any] = {
        "from_": _format_whatsapp_number(from_number),
        "to": _format_whatsapp_number(phone_number),
    }

    if content_sid:
        payload["content_sid"] = content_sid
        payload["content_variables"] = json.dumps({"1": patient_name, "2": pdf_url})
    else:
        payload["body"] = (
            f"Hello {patient_name}, your SehatSaathi clinical report is ready. "
            f"Download it here: {pdf_url}"
        )

    try:
        message = _get_client().messages.create(**payload)
    except TwilioRestException as exc:  # pragma: no cover - network/service side
        raise WhatsAppConfigError(f"Twilio WhatsApp send failed: {exc}") from exc

    return {
        "message_sid": message.sid,
        "to": payload["to"],
    }
