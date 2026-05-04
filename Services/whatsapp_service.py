import os
from typing import Any

from dotenv import load_dotenv
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

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
        raise WhatsAppConfigError("Invalid phone number.")

    if not normalized.startswith("+"):
        normalized = f"+{normalized}"

    return f"whatsapp:{normalized}"


def _get_client() -> Client:
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")

    if not account_sid or not auth_token:
        raise WhatsAppConfigError("Twilio credentials missing.")

    return Client(account_sid, auth_token)


def send_report_whatsapp_message(report: dict[str, Any], pdf_url: str = "") -> dict[str, str]:
    if not is_whatsapp_enabled():
        raise WhatsAppConfigError("WhatsApp not configured.")

    # 🔥 Always send to your sandbox number
    phone_number = "+918769140658"

    from_number = os.getenv("TWILIO_WHATSAPP_FROM")
    patient_name = report.get("patient_name") or "Patient"

    payload = {
        "from_": _format_whatsapp_number(from_number),
        "to": _format_whatsapp_number(phone_number),

        # 🔥 ONLY TEXT MESSAGE (NO PDF)
        "body": (
            f"Hi {patient_name} 👋\n\n"
            f"This is a test message from SehatSaathi.\n\n"
            f"Lorem ipsum dolor sit amet 🚀"
        ),
    }

    try:
        message = _get_client().messages.create(**payload)
    except TwilioRestException as exc:
        raise WhatsAppConfigError(f"Twilio send failed: {exc}") from exc

    return {
        "message_sid": message.sid,
        "to": payload["to"],
    }