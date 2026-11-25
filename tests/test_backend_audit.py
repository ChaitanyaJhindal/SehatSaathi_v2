import base64
import os
import tempfile
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

import app as backend_app
from Services import Reasoning, STT, pdf_service, whatsapp_service


class BackendAuditTestSuite(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(backend_app.app)

    def test_app_imports_re_and_lazy_clients(self):
        self.assertIn("re", vars(backend_app))
        # Ensure missing API keys do not fail module import; only fail at call time
        with patch.dict(
            os.environ,
            {"GROQ_API_KEY": "", "SARVAM_API_KEY": "", "SARVAM_FALLBACK_API_KEY": ""},
            clear=False,
        ):
            Reasoning._groq_client = None
            STT._sarvam_client = None
            with self.assertRaises(RuntimeError):
                Reasoning._get_groq_client()
            with self.assertRaises(RuntimeError):
                STT._get_sarvam_client()

    def test_auth_required_on_protected_routes(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertEqual(self.client.get("/reports").status_code, 401)
        self.assertEqual(self.client.get("/whatsapp/status").status_code, 401)
        self.assertEqual(self.client.post("/whatsapp/connect").status_code, 401)

    def test_invalid_email_returns_422_list_detail(self):
        resp = self.client.post("/auth/login", json={"email": "not-an-email", "password": "secret"})
        self.assertEqual(resp.status_code, 422)
        body = resp.json()
        self.assertIsInstance(body["detail"], list)

    def test_download_report_rejects_regex_leak_tokens(self):
        # Previously /report/download/report or /report/download/a matched any report via regex
        for bad_token in ["report", "download", "a", "..%2Fsecret", "short"]:
            resp = self.client.get(f"/report/download/{bad_token}")
            self.assertIn(resp.status_code, (400, 404), msg=f"Unexpected status for {bad_token}")

    def test_pdf_generation_handles_xml_chars_age_zero_dr_prefix_and_dosage(self):
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
        os.close(tmp_fd)
        try:
            report = {
                "clinic_name": "City Care & Cure",
                "doctor_name": "Dr. Meera Sharma",
                "doctor_dept": "Cardiology",
                "clinic_address": "12 MG Road, Sector 4 <Block A>, Bengaluru",
                "patient_name": "Baby A & B",
                "patient_age": 0,
                "patient_gender": "Female",
                "patient_mobile": "+919876543210",
                "diagnosis": "Temp > 101 & <mild> viral fever",
                "symptoms": ["Fever < 102F", "Cough & cold"],
                "medications": ["Paracetamol 250mg"],
                "dosage": ["5ml every 6 hours after food"],
                "precautions": ["Hydration & rest"],
                "follow_up": "Review after 3 days",
                "doctor_notes": "Monitor temperature < 103F.",
            }
            out = pdf_service.generate_pdf(report, tmp_path)
            self.assertTrue(os.path.exists(out))
            self.assertGreater(os.path.getsize(out), 1000)
            self.assertEqual(pdf_service._format_doctor_name("Dr. Meera Sharma"), "Dr. Meera Sharma")
            self.assertEqual(pdf_service._format_doctor_name("Meera Sharma"), "Dr. Meera Sharma")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_patch_report_updates_and_regenerates_pdf(self):
        token = "a" * 32
        fake_doctor = {
            "id": "doc_123",
            "name": "Dr. Meera Sharma",
            "email": "meera@clinic.in",
            "specialization": "General Medicine",
            "organization_name": "Care Clinic",
        }
        updated_doc = {
            "id": "mongo_1",
            "report_id": "rep_1",
            "doctor_id": "doc_123",
            "patient_name": "Rohan Verma",
            "patient_age": 42,
            "patient_gender": "Male",
            "patient_phone": "+919811112222",
            "symptoms": ["High fever"],
            "diagnosis": "Updated Viral Fever",
            "medications": ["Paracetamol 650mg"],
            "dosage": ["1 tablet SOS"],
            "precautions": ["Rest"],
            "follow_up": "In 2 days",
            "doctor_notes": "Updated notes",
            "pdf_url": f"/report/download/{token}",
        }

        backend_app.app.dependency_overrides[backend_app.get_current_doctor] = lambda: fake_doctor
        expected_pdf = backend_app._safe_pdf_path(token)
        try:
            with patch("app.update_report_record", return_value=updated_doc) as mock_update:
                resp = self.client.patch(
                    "/reports/rep_1",
                    json={"diagnosis": "Updated Viral Fever", "dosage": ["1 tablet SOS"]},
                )
            self.assertEqual(resp.status_code, 200)
            mock_update.assert_called_once()
            self.assertTrue(os.path.exists(expected_pdf))
            dl = self.client.get(f"/report/download/{token}")
            self.assertEqual(dl.status_code, 200)
            self.assertEqual(dl.headers["content-type"], "application/pdf")
        finally:
            backend_app.app.dependency_overrides.clear()
            if os.path.exists(expected_pdf):
                os.remove(expected_pdf)

    def test_openwa_phone_formatting(self):
        self.assertEqual(whatsapp_service.format_chat_id("9876543210"), "919876543210@c.us")
        self.assertEqual(whatsapp_service.format_chat_id("09876543210"), "919876543210@c.us")
        self.assertEqual(whatsapp_service.format_chat_id("+91 98765-43210"), "919876543210@c.us")
        self.assertEqual(whatsapp_service.format_chat_id("919876543210@c.us"), "919876543210@c.us")
        with self.assertRaises(whatsapp_service.WhatsAppValidationError):
            whatsapp_service.format_chat_id("")
        with self.assertRaises(whatsapp_service.WhatsAppValidationError):
            whatsapp_service.format_chat_id("12345")

    def test_whatsapp_connect_qr_and_send_document(self):
        calls = []
        state = {"status": "not_created"}

        def fake_request(method, path, *, json_body=None, timeout=25.0):
            calls.append((method, path, json_body))
            req = httpx.Request(method, f"http://127.0.0.1:2785{path}")

            if method == "POST" and path == "/sessions/sehatsaathi-doc123/connect":
                state["status"] = "qr_ready"
                return httpx.Response(200, json={
                    "gateway_reachable": True,
                    "configured": True,
                    "session_id": "sehatsaathi-doc123",
                    "session_name": "sehatsaathi-doc123",
                    "status": "qr_ready",
                    "connected": False,
                    "qr_code": "data:image/png;base64,FAKEQRDATA",
                }, request=req)

            if method == "POST" and path == "/sessions/sehatsaathi-doc123/send-document":
                if state["status"] != "ready":
                    return httpx.Response(409, json={"message": "Not connected"}, request=req)
                return httpx.Response(201, json={
                    "id": "msg_abc123",
                    "to": "919876543210@s.whatsapp.net",
                }, request=req)

            return httpx.Response(404, json={"message": "Not found"}, request=req)

        tmp_fd, pdf_path = tempfile.mkstemp(suffix=".pdf")
        os.write(tmp_fd, b"%PDF-1.4 mock pdf")
        os.close(tmp_fd)

        try:
            with patch("Services.whatsapp_service._bridge_request", side_effect=fake_request):
                connect_res = whatsapp_service.connect_whatsapp_session("doc123")
                self.assertEqual(connect_res["status"], "qr_ready")
                self.assertEqual(connect_res["qr_code"], "data:image/png;base64,FAKEQRDATA")

                state["status"] = "ready"

                send_res = whatsapp_service.send_report_whatsapp_message(
                    {"patient_name": "Rohan", "patient_phone": "9876543210", "diagnosis": "Flu"},
                    pdf_path=pdf_path,
                    doctor_id="doc123",
                )
                self.assertEqual(send_res["delivery"], "document")
                self.assertEqual(send_res["to"], "919876543210@s.whatsapp.net")
                self.assertEqual(send_res["message_id"], "msg_abc123")

                doc_call = [c for c in calls if c[1].endswith("/send-document")][0]
                self.assertEqual(doc_call[2]["mimetype"], "application/pdf")
                self.assertEqual(doc_call[2]["chatId"], "919876543210@c.us")
                self.assertEqual(
                    base64.b64decode(doc_call[2]["base64"]),
                    b"%PDF-1.4 mock pdf",
                )
        finally:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)

    def test_whatsapp_not_connected_raises_409_error(self):
        req = httpx.Request("POST", "http://127.0.0.1:2785/sessions/sehatsaathi-doc123/send-text")
        with patch(
            "Services.whatsapp_service._bridge_request",
            return_value=httpx.Response(409, json={"message": "Not connected"}, request=req),
        ):
            with self.assertRaises(whatsapp_service.WhatsAppNotConnectedError):
                whatsapp_service.send_report_whatsapp_message(
                    {"patient_name": "Rohan", "patient_phone": "9876543210"},
                    doctor_id="doc123",
                )


if __name__ == "__main__":
    unittest.main()
