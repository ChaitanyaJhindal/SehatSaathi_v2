from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _text(value, fallback="-"):
    if value is None:
        return fallback
    value = str(value).strip()
    return value if value else fallback


def _items(values):
    if not values:
        return []
    if isinstance(values, list):
        return [str(item).strip() for item in values if str(item).strip()]
    value = str(values).strip()
    return [value] if value else []


def build_pdf(final_data: dict, output_file: str = "clinical_report.pdf"):
    def make_styles():
        s = getSampleStyleSheet()
        defs = [
            ("ClinicName", "Helvetica-Bold", 20, colors.HexColor("#1a3c5e"), TA_LEFT),
            ("ClinicTagline", "Helvetica", 9, colors.HexColor("#d0e4f7"), TA_LEFT),
            ("ClinicAddress", "Helvetica-Bold", 11, colors.HexColor("#1a3c5e"), TA_RIGHT),
            ("ReportTitle", "Helvetica-Bold", 12, colors.HexColor("#1a3c5e"), TA_CENTER),
            ("InfoLabel", "Helvetica-Bold", 9, colors.HexColor("#444444"), TA_LEFT),
            ("InfoValue", "Helvetica", 9, colors.black, TA_LEFT),
            ("BulletItem", "Helvetica", 9, colors.black, TA_LEFT),
            ("NormalSmall", "Helvetica", 9, colors.black, TA_LEFT),
        ]
        for name, font, size, color, align in defs:
            s.add(
                ParagraphStyle(
                    name=name,
                    fontName=font,
                    fontSize=size,
                    textColor=color,
                    alignment=align,
                    leading=size + 4,
                )
            )
        return s

    styles = make_styles()

    doc = SimpleDocTemplate(
        output_file,
        pagesize=A4,
        rightMargin=1.8 * cm,
        leftMargin=1.8 * cm,
        topMargin=1.8 * cm,
        bottomMargin=2 * cm,
    )

    elems = []
    usable_w = doc.width

    def info_row(label, value):
        return [
            Paragraph(label, styles["InfoLabel"]),
            Paragraph(":", styles["InfoLabel"]),
            Paragraph(_text(value), styles["InfoValue"]),
        ]

    def section_header(title):
        t = Table([[Paragraph(title, styles["InfoLabel"])]], colWidths=[usable_w])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1a3c5e")),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        return t

    elems.append(
        Paragraph(_text(final_data.get("clinic_name"), "SehatSaathi Clinic"), styles["ClinicName"])
    )
    elems.append(Spacer(1, 10))

    elems.append(Paragraph("Clinical Consultation Report", styles["ReportTitle"]))
    elems.append(HRFlowable(width="100%", thickness=1.2, color=colors.grey))
    elems.append(Spacer(1, 10))

    info = [
        info_row("Patient Name", final_data.get("patient_name")),
        info_row(
            "Age/Gender",
            f"{_text(final_data.get('patient_age', final_data.get('age')))} / "
            f"{_text(final_data.get('patient_gender', final_data.get('gender')))}",
        ),
        info_row("Doctor", final_data.get("doctor_name")),
        info_row("Diagnosis", final_data.get("diagnosis")),
    ]

    table = Table(info, colWidths=[4 * cm, 1 * cm, usable_w - 5 * cm])
    elems.append(table)
    elems.append(Spacer(1, 12))

    elems.append(section_header("Symptoms"))
    symptoms = _items(final_data.get("symptoms"))
    if symptoms:
        for symptom in symptoms:
            elems.append(Paragraph(f"* {symptom}", styles["BulletItem"]))
    else:
        elems.append(Paragraph("-", styles["NormalSmall"]))
    elems.append(Spacer(1, 10))

    elems.append(section_header("Medications"))
    medications = _items(final_data.get("medications"))
    if medications:
        for medication in medications:
            elems.append(Paragraph(f"* {medication}", styles["BulletItem"]))
    else:
        elems.append(Paragraph("-", styles["NormalSmall"]))
    elems.append(Spacer(1, 10))

    elems.append(section_header("Precautions"))
    precautions = _items(final_data.get("precautions"))
    if precautions:
        for precaution in precautions:
            elems.append(Paragraph(f"* {precaution}", styles["BulletItem"]))
    else:
        elems.append(Paragraph("-", styles["NormalSmall"]))
    elems.append(Spacer(1, 10))

    elems.append(section_header("Doctor Notes"))
    elems.append(Paragraph(_text(final_data.get("doctor_notes"), ""), styles["NormalSmall"]))

    doc.build(elems)
    return output_file


def generate_pdf(report: dict, output_file="clinical_report.pdf"):
    final_data = {
        "clinic_name": report.get("clinic_name") or "SehatSaathi Clinic",
        "patient_name": report.get("patient_name"),
        "patient_age": report.get("patient_age", report.get("age")),
        "patient_gender": report.get("patient_gender", report.get("gender")),
        "doctor_name": report.get("doctor_name"),
        "diagnosis": report.get("diagnosis"),
        "symptoms": report.get("symptoms", []),
        "medications": report.get("medications", []),
        "precautions": report.get("precautions", []),
        "doctor_notes": report.get("doctor_notes", ""),
    }
    return build_pdf(final_data, output_file=output_file)
