import re
import unicodedata
from xml.sax.saxutils import escape as xml_escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _text(value, fallback="--", escape_xml=True):
    if value is None:
        return fallback

    value = str(value).strip()
    if not value:
        return fallback

    value = unicodedata.normalize("NFKC", value)
    replacements = {
        "â€”": "-",
        "â€¢": "-",
        "\u00a0": " ",
        "\u2022": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u20b9": "Rs.",
        "\u00b0": " deg ",
    }
    for source, target in replacements.items():
        value = value.replace(source, target)

    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\x20-\x7E]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()

    if not value:
        return fallback

    return xml_escape(value) if escape_xml else value


def _items(values):
    if not values:
        return []
    if isinstance(values, list):
        cleaned = []
        for item in values:
            raw = _text(item, "", escape_xml=False)
            if raw:
                cleaned.append(raw)
        return cleaned
    if isinstance(values, str):
        return [_text(line, "", escape_xml=False) for line in values.splitlines() if _text(line, "", escape_xml=False)]
    value = _text(values, "", escape_xml=False)
    return [value] if value else []


def _format_doctor_name(name) -> str:
    raw = _text(name, "", escape_xml=False)
    if not raw:
        return "--"
    stripped = re.sub(r"^(?:dr\.?\s+)+", "", raw, flags=re.IGNORECASE).strip()
    return f"Dr. {xml_escape(stripped)}" if stripped else "--"


def build_pdf(final_data: dict, output_file="clinical_report.pdf"):
    header_bg = colors.HexColor("#1a3c5e")
    header_text = colors.white
    section_bg = colors.HexColor("#e8f0f7")
    label_color = colors.HexColor("#1a3c5e")
    table_border = colors.HexColor("#b0c4de")

    def make_styles():
        styles = getSampleStyleSheet()
        defs = [
            ("ClinicName", "Helvetica-Bold", 19, header_text, TA_LEFT),
            ("ClinicTagline", "Helvetica", 9, colors.HexColor("#d0e4f7"), TA_LEFT),
            ("ClinicAddress", "Helvetica-Bold", 10, colors.white, TA_RIGHT),
            ("ReportTitle", "Helvetica-Bold", 12, label_color, TA_CENTER),
            ("InfoLabel", "Helvetica-Bold", 9, colors.HexColor("#444444"), TA_LEFT),
            ("InfoValue", "Helvetica", 9, colors.black, TA_LEFT),
            ("BulletItem", "Helvetica", 9, colors.black, TA_LEFT),
            ("NormalSmall", "Helvetica", 9, colors.black, TA_LEFT),
        ]
        for name, font, size, color, align in defs:
            styles.add(ParagraphStyle(
                name=name,
                fontName=font,
                fontSize=size,
                textColor=color,
                alignment=align,
                leading=size + 4,
            ))
        return styles

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

    def info_row(label, value, already_escaped=False):
        rendered_val = value if already_escaped else _text(value)
        return [
            Paragraph(_text(label), styles["InfoLabel"]),
            Paragraph(":", styles["InfoLabel"]),
            Paragraph(rendered_val, styles["InfoValue"]),
        ]

    def section_header(title):
        table = Table(
            [[
                Paragraph(
                    _text(title),
                    ParagraphStyle(
                        "SectionHeader",
                        fontName="Helvetica-Bold",
                        fontSize=10,
                        textColor=colors.white,
                        leading=14,
                    ),
                )
            ]],
            colWidths=[usable_w],
        )

        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), header_bg),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        return table

    doctor_display = _format_doctor_name(final_data.get("doctor_name"))
    dept_display = _text(final_data.get("doctor_dept"))
    left_w = usable_w * 0.58
    right_w = usable_w * 0.42

    header_left = Table(
        [
            [Paragraph(_text(final_data.get("clinic_name")), styles["ClinicName"])],
            [Paragraph(f"{doctor_display} - {dept_display}", styles["ClinicTagline"])],
        ],
        colWidths=[left_w - 24],
    )

    address_escaped = _text(final_data.get("clinic_address"), fallback="--", escape_xml=True)
    address_html = address_escaped.replace(",", "<br/>")
    header_right = Table(
        [[Paragraph(address_html, styles["ClinicAddress"])]],
        colWidths=[right_w - 24],
    )

    header_table = Table(
        [[header_left, header_right]],
        colWidths=[left_w, right_w],
    )

    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), header_bg),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    elems.append(header_table)
    elems.append(Spacer(1, 10))

    elems.append(Paragraph("Clinical Consultation Report", styles["ReportTitle"]))
    elems.append(HRFlowable(width="100%", thickness=1.5, color=label_color))
    elems.append(Spacer(1, 10))

    age_text = _text(final_data.get("patient_age"))
    gender_text = _text(final_data.get("patient_gender"))

    left_info = [
        info_row("Patient Name", final_data.get("patient_name")),
        info_row("Age / Gender", f"{age_text} / {gender_text}", already_escaped=True),
        info_row("Doctor", doctor_display, already_escaped=True),
    ]

    right_info = [
        info_row("Diagnosis", final_data.get("diagnosis")),
        info_row("Visit Type", final_data.get("visit_type")),
        info_row("Mobile", final_data.get("patient_mobile")),
    ]

    half_w = usable_w / 2
    inner_cols = [2.4 * cm, 0.35 * cm, max(2.0 * cm, half_w - 2.9 * cm)]

    left_table = Table(left_info, colWidths=inner_cols)
    right_table = Table(right_info, colWidths=inner_cols)
    for tbl in (left_table, right_table):
        tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))

    patient_block = Table([[left_table, right_table]], colWidths=[half_w, half_w])
    patient_block.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), section_bg),
        ("BOX", (0, 0), (-1, -1), 0.5, table_border),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    elems.append(patient_block)
    elems.append(Spacer(1, 14))

    elems.append(section_header("Symptoms"))
    elems.append(Spacer(1, 6))
    symptoms = _items(final_data.get("symptoms"))
    for symptom in symptoms or ["No symptoms mentioned"]:
        elems.append(Paragraph(f"- {xml_escape(symptom)}", styles["BulletItem"]))
    elems.append(Spacer(1, 10))

    elems.append(section_header("Medications"))
    elems.append(Spacer(1, 6))
    medications = _items(final_data.get("medications"))
    if medications:
        med_data = [[
            Paragraph("#", styles["InfoLabel"]),
            Paragraph("Medicine / Prescription", styles["InfoLabel"]),
        ]]

        for index, medication in enumerate(medications, 1):
            med_data.append([
                Paragraph(str(index), styles["NormalSmall"]),
                Paragraph(xml_escape(medication), styles["NormalSmall"]),
            ])

        med_table = Table(med_data, colWidths=[1 * cm, usable_w - 1 * cm])
        med_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d0dce8")),
            ("GRID", (0, 0), (-1, -1), 0.4, table_border),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f8fc")]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elems.append(med_table)
    else:
        elems.append(Paragraph("No medications prescribed.", styles["NormalSmall"]))

    elems.append(Spacer(1, 10))

    dosage_items = _items(final_data.get("dosage"))
    elems.append(section_header("Dosage Instructions"))
    elems.append(Spacer(1, 6))
    for item in dosage_items or ["No specific dosage notes"]:
        elems.append(Paragraph(f"- {xml_escape(item)}", styles["BulletItem"]))
    elems.append(Spacer(1, 10))

    elems.append(section_header("Precautions"))
    elems.append(Spacer(1, 6))
    precautions = _items(final_data.get("precautions"))
    for precaution in precautions or ["No precautions"]:
        elems.append(Paragraph(f"- {xml_escape(precaution)}", styles["BulletItem"]))
    elems.append(Spacer(1, 10))

    follow_up_text = _text(final_data.get("follow_up"), fallback="")
    if follow_up_text:
        elems.append(section_header("Follow-Up"))
        elems.append(Spacer(1, 6))
        elems.append(Paragraph(follow_up_text, styles["NormalSmall"]))
        elems.append(Spacer(1, 10))

    elems.append(section_header("Doctor Notes"))
    elems.append(Spacer(1, 6))
    elems.append(Paragraph(_text(final_data.get("doctor_notes")), styles["NormalSmall"]))

    doc.build(elems)
    return output_file


def generate_pdf(report: dict, output_file="clinical_report.pdf"):
    patient_age = report.get("patient_age")
    if patient_age is None:
        patient_age = report.get("age")

    final_data = {
        "clinic_name": report.get("clinic_name") or report.get("organization_name") or "SehatSaathi Clinic",
        "doctor_name": report.get("doctor_name"),
        "doctor_dept": report.get("doctor_dept") or report.get("specialization"),
        "clinic_address": report.get("clinic_address"),
        "patient_name": report.get("patient_name"),
        "patient_age": patient_age,
        "patient_gender": report.get("patient_gender") or report.get("gender"),
        "patient_mobile": report.get("patient_mobile") or report.get("patient_phone"),
        "visit_type": report.get("visit_type") or "Consultation",
        "diagnosis": report.get("diagnosis"),
        "symptoms": report.get("symptoms", []),
        "medications": report.get("medications", []),
        "dosage": report.get("dosage", []),
        "precautions": report.get("precautions", []),
        "follow_up": report.get("follow_up", ""),
        "doctor_notes": report.get("doctor_notes", ""),
    }

    return build_pdf(final_data, output_file)
