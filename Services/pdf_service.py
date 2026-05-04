import unicodedata

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _text(value, fallback="--"):
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
    }
    for source, target in replacements.items():
        value = value.replace(source, target)

    return value


def _items(values):
    if not values:
        return []
    if isinstance(values, list):
        return [_text(v, "") for v in values if _text(v, "")]
    value = _text(values, "")
    return [value] if value else []


def build_pdf(final_data: dict, output_file="clinical_report.pdf"):
    header_bg = colors.HexColor("#1a3c5e")
    header_text = colors.white
    section_bg = colors.HexColor("#e8f0f7")
    label_color = colors.HexColor("#1a3c5e")
    table_border = colors.HexColor("#b0c4de")

    def make_styles():
        styles = getSampleStyleSheet()
        defs = [
            ("ClinicName", "Helvetica-Bold", 20, header_text, TA_LEFT),
            ("ClinicTagline", "Helvetica", 9, colors.HexColor("#d0e4f7"), TA_LEFT),
            ("ClinicAddress", "Helvetica-Bold", 11, colors.white, TA_RIGHT),
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

    def info_row(label, value):
        return [
            Paragraph(_text(label), styles["InfoLabel"]),
            Paragraph(":", styles["InfoLabel"]),
            Paragraph(_text(value), styles["InfoValue"]),
        ]

    def section_header(title):
        table = Table([[
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
        ]], colWidths=[usable_w])

        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), header_bg),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        return table

    header_left = [
        [Paragraph(_text(final_data.get("clinic_name")), styles["ClinicName"])],
        [Paragraph(
            f"Dr. {_text(final_data.get('doctor_name'))} - {_text(final_data.get('doctor_dept'))}",
            styles["ClinicTagline"],
        )],
    ]

    header_right = [[
        Paragraph(
            _text(final_data.get("clinic_address")).replace(",", "<br/>"),
            styles["ClinicAddress"],
        )
    ]]

    header_table = Table(
        [[Table(header_left), Table(header_right)]],
        colWidths=[usable_w * 0.55, usable_w * 0.45],
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

    left_info = [
        info_row("Patient Name", final_data.get("patient_name")),
        info_row("Age / Gender", f"{_text(final_data.get('patient_age'))} / {_text(final_data.get('patient_gender'))}"),
        info_row("Doctor", final_data.get("doctor_name")),
    ]

    right_info = [
        info_row("Diagnosis", final_data.get("diagnosis")),
        info_row("Visit Type", final_data.get("visit_type")),
        info_row("Mobile", final_data.get("patient_mobile")),
    ]

    left_table = Table(left_info)
    right_table = Table(right_info)

    patient_block = Table([[left_table, right_table]], colWidths=[usable_w / 2, usable_w / 2])
    patient_block.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), section_bg),
        ("BOX", (0, 0), (-1, -1), 0.5, table_border),
    ]))

    elems.append(patient_block)
    elems.append(Spacer(1, 14))

    elems.append(section_header("Symptoms"))
    elems.append(Spacer(1, 6))
    symptoms = _items(final_data.get("symptoms"))
    for symptom in symptoms or ["No symptoms mentioned"]:
        elems.append(Paragraph(f"- {_text(symptom)}", styles["BulletItem"]))
    elems.append(Spacer(1, 10))

    elems.append(section_header("Medications"))
    elems.append(Spacer(1, 6))

    medications = _items(final_data.get("medications"))
    if medications:
        med_data = [[
            Paragraph("#", styles["InfoLabel"]),
            Paragraph("Medicine / Dosage", styles["InfoLabel"]),
        ]]

        for index, medication in enumerate(medications, 1):
            med_data.append([
                Paragraph(str(index), styles["NormalSmall"]),
                Paragraph(_text(medication), styles["NormalSmall"]),
            ])

        med_table = Table(med_data, colWidths=[1 * cm, usable_w - 1 * cm])
        med_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d0dce8")),
            ("GRID", (0, 0), (-1, -1), 0.4, table_border),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f8fc")]),
        ]))

        elems.append(med_table)
    else:
        elems.append(Paragraph("No medications prescribed.", styles["NormalSmall"]))

    elems.append(Spacer(1, 10))

    elems.append(section_header("Precautions"))
    elems.append(Spacer(1, 6))
    precautions = _items(final_data.get("precautions"))
    for precaution in precautions or ["No precautions"]:
        elems.append(Paragraph(f"- {_text(precaution)}", styles["BulletItem"]))
    elems.append(Spacer(1, 10))

    elems.append(section_header("Doctor Notes"))
    elems.append(Spacer(1, 6))
    elems.append(Paragraph(_text(final_data.get("doctor_notes")), styles["NormalSmall"]))

    doc.build(elems)
    return output_file


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
