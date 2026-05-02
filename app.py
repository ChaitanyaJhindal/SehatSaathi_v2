import os
import tempfile
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from Services.db_service import (
    DatabaseConfigError,
    create_report_record,
    get_patient_details,
)
from Services.Reasoning import generate_clinical_report
from Services.pdf_service import generate_pdf

app = FastAPI(title="SehatSaathi API", version="1.0.0")


def _cleanup_files(paths: list[str]) -> None:
    for path in paths:
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except OSError:
            pass


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/report/pdf")
async def create_report_pdf(
    background_tasks: BackgroundTasks,
    patient_id: str = Form(...),
    audio: UploadFile = File(...)
):
    if not audio.filename:
        raise HTTPException(status_code=400, detail="Audio file is required.")

    try:
        patient = get_patient_details(patient_id)
    except DatabaseConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to fetch patient details.") from exc

    suffix = os.path.splitext(audio.filename)[1] or ".wav"
    temp_dir = tempfile.gettempdir()
    audio_path = os.path.join(temp_dir, f"ss_audio_{uuid4().hex}{suffix}")

    with open(audio_path, "wb") as f:
        content = await audio.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty audio file.")
        f.write(content)

    try:
        report = generate_clinical_report(audio_path, patient_context=patient)
    except Exception as exc:
        _cleanup_files([audio_path])
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    report_id = str(uuid4())
    report["id"] = report_id
    report["report_id"] = report_id
    report["patient_id"] = patient.get("id")
    report["doctor_name"] = patient.get("doctor_name")

    pdf_name = f"clinical_report_{uuid4().hex}.pdf"
    pdf_path = os.path.join(temp_dir, pdf_name)

    try:
        generate_pdf(report, pdf_path)
    except Exception as exc:
        _cleanup_files([audio_path, pdf_path])
        raise HTTPException(status_code=500, detail="Failed to generate PDF.") from exc

    try:
        create_report_record(report, patient)
    except Exception as exc:
        _cleanup_files([audio_path, pdf_path])
        raise HTTPException(status_code=500, detail=f"Failed to save report: {exc}") from exc

    background_tasks.add_task(_cleanup_files, [audio_path, pdf_path])

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename="clinical_report.pdf"
    )
