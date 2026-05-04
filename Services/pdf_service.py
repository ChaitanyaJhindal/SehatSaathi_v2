from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable, Paragraph, SimpleDocTemplate,
    Spacer, Table, TableStyle
)


# ---------- SAFE HELPERS ----------
def _text(value, fallback="—"):
    if value is None:
        return fallback
    value = str(value).strip()
    return value if value else fallback


def _items(values):
    if not values:
        return []
    if isinstance(values, list):
        return [str(v).strip() for v in values if str(v).strip()]
    value = str(values).strip()
    return [value] if value else []


# ---------- MAIN PDF ----------
def build_pdf(final_data: dict, output_file="clinical_report.pdf"):

    HEADER_BG = colors.HexColor("#1a3c5e")
    HEADER_TEXT = colors.white
    SECTION_BG = colors.HexColor("#e8f0f7")
    LABEL_COLOR = colors.HexColor("#1a3c5e")
    TABLE_BORDER = colors.HexColor("#b0c4de")

    def make_styles():
        s = getSampleStyleSheet()
        defs = [
            ("ClinicName", "Helvetica-Bold", 20, HEADER_TEXT, TA_LEFT),
            ("ClinicTagline", "Helvetica", 9, colors.HexColor("#d0e4f7"), TA_LEFT),
            ("ClinicAddress", "Helvetica-Bold", 11, colors.white, TA_RIGHT),
            ("ReportTitle", "Helvetica-Bold", 12, LABEL_COLOR, TA_CENTER),
            ("InfoLabel", "Helvetica-Bold", 9, colors.HexColor("#444444"), TA_LEFT),
            ("InfoValue", "Helvetica", 9, colors.black, TA_LEFT),
            ("BulletItem", "Helvetica", 9, colors.black, TA_LEFT),
            ("NormalSmall", "Helvetica", 9, colors.black, TA_LEFT),
        ]
        for name, font, size, color, align in defs:
            s.add(ParagraphStyle(
                name=name,
                fontName=font,
                fontSize=size,
                textColor=color,
                alignment=align,
                leading=size + 4
            ))
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
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        return t

    # ---------- HEADER ----------
    header_left = [
        [Paragraph(_text(final_data.get("clinic_name")), styles["ClinicName"])],
        [Paragraph(
            f"Dr. {_text(final_data.get('doctor_name'))} • {_text(final_data.get('doctor_dept'))}",
            styles["ClinicTagline"]
        )],
    ]

    header_right = [[
        Paragraph(
            _text(final_data.get("clinic_address")).replace(",", "<br/>"),
            styles["ClinicAddress"]
        )
    ]]

    header_table = Table(
        [[Table(header_left), Table(header_right)]],
        colWidths=[usable_w * 0.55, usable_w * 0.45]
    )

    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HEADER_BG),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    elems.append(header_table)
    elems.append(Spacer(1, 10))

    # ---------- TITLE ----------
    elems.append(Paragraph("Clinical Consultation Report", styles["ReportTitle"]))
    elems.append(HRFlowable(width="100%", thickness=1.5, color=LABEL_COLOR))
    elems.append(Spacer(1, 10))

    # ---------- PATIENT BLOCK ----------
    left_info = [
        info_row("Patient Name", final_data.get("patient_name")),
        info_row("Age / Gender",
                 f"{_text(final_data.get('patient_age'))} / {_text(final_data.get('patient_gender'))}"),
        info_row("Doctor", final_data.get("doctor_name")),
    ]

    right_info = [
        info_row("Diagnosis", final_data.get("diagnosis")),
        info_row("Visit Type", final_data.get("visit_type")),
        info_row("Mobile", final_data.get("patient_mobile")),
    ]

    lt = Table(left_info)
    rt = Table(right_info)

    pb = Table([[lt, rt]], colWidths=[usable_w / 2, usable_w / 2])
    pb.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SECTION_BG),
        ("BOX", (0, 0), (-1, -1), 0.5, TABLE_BORDER),
    ]))

    elems.append(pb)
    elems.append(Spacer(1, 14))

    # ---------- SYMPTOMS ----------
    elems.append(section_header("Symptoms"))
    symptoms = _items(final_data.get("symptoms"))
    for s in symptoms or ["No symptoms mentioned"]:
        elems.append(Paragraph(f"• {s}", styles["BulletItem"]))
    elems.append(Spacer(1, 10))

    # ---------- MEDICATIONS ----------
    elems.append(section_header("Medications"))
    medications = _items(final_data.get("medications"))
    for m in medications or ["No medications"]:
        elems.append(Paragraph(f"• {m}", styles["BulletItem"]))
    elems.append(Spacer(1, 10))

    # ---------- PRECAUTIONS ----------
    elems.append(section_header("Precautions"))
    precautions = _items(final_data.get("precautions"))
    for p in precautions or ["No precautions"]:
        elems.append(Paragraph(f"• {p}", styles["BulletItem"]))
    elems.append(Spacer(1, 10))

    # ---------- NOTES ----------
    elems.append(section_header("Doctor Notes"))
    elems.append(Paragraph(_text(final_data.get("doctor_notes")), styles["NormalSmall"]))

    doc.build(elems)
    return output_file


# ---------- API FUNCTION ----------
def generate_pdf(report: dict, output_file="clinical_report.pdf"):
    final_data = {
        "clinic_name": report.get("clinic_name") or "SehatSaathi Clinic",
        "doctor_name": report.get("doctor_name"),
        "doctor_dept": report.get("doctor_dept"),
        "clinic_address": report.get("clinic_address"),
        "patient_name": report.get("patient_name"),
        "patient_age": report.get("patient_age"),
        "patient_gender": report.get("patient_gender"),
        "patient_mobile": report.get("patient_mobile"),
        "visit_type": report.get("visit_type"),
        "diagnosis": report.get("diagnosis"),
        "symptoms": report.get("symptoms", []),
        "medications": report.get("medications", []),
        "precautions": report.get("precautions", []),
        "doctor_notes": report.get("doctor_notes", ""),
    }

    return build_pdf(final_data, output_file)