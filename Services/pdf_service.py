from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


PAGE_WIDTH, PAGE_HEIGHT = A4
LEFT_RIGHT_MARGIN = 18 * mm
TOP_MARGIN = 42 * mm
BOTTOM_MARGIN = 40 * mm

PRIMARY = colors.HexColor("#005EA4")
PRIMARY_LIGHT = colors.HexColor("#D3E4FF")
SECONDARY = colors.HexColor("#526069")
TERTIARY = colors.HexColor("#8F4A00")
BACKGROUND = colors.HexColor("#FCF9F8")
BORDER = colors.HexColor("#C0C7D4")
TEXT = colors.HexColor("#1B1C1C")
SUBTEXT = colors.HexColor("#404752")
SURFACE_LOW = colors.HexColor("#F6F3F2")
WHITE = colors.white


def _stringify(value, fallback="N/A"):
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def _listify(values):
    if not values:
        return []
    if isinstance(values, list):
        return [str(item).strip() for item in values if str(item).strip()]
    return [str(values).strip()] if str(values).strip() else []


def _split_dosage_entry(entry: str):
    parts = [part.strip() for part in entry.split("|")]
    if len(parts) >= 3:
        return parts[0], parts[1], parts[2]
    if len(parts) == 2:
        return parts[0], parts[1], "As advised"
    return entry.strip(), "As prescribed", "As advised"


def _build_styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=20,
            textColor=TEXT,
            alignment=TA_LEFT,
            spaceAfter=2,
        ),
        "kicker": ParagraphStyle(
            "Kicker",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=SUBTEXT,
            alignment=TA_LEFT,
            spaceAfter=0,
        ),
        "headerMeta": ParagraphStyle(
            "HeaderMeta",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=SUBTEXT,
            alignment=TA_RIGHT,
        ),
        "section": ParagraphStyle(
            "Section",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=TEXT,
            spaceAfter=8,
        ),
        "label": ParagraphStyle(
            "Label",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=SUBTEXT,
        ),
        "value": ParagraphStyle(
            "Value",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=TEXT,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=SUBTEXT,
        ),
        "bodyDark": ParagraphStyle(
            "BodyDark",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=TEXT,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=SUBTEXT,
            leftIndent=10,
            bulletIndent=0,
            spaceAfter=2,
        ),
        "footer": ParagraphStyle(
            "Footer",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=TEXT,
        ),
        "footerMuted": ParagraphStyle(
            "FooterMuted",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=SUBTEXT,
        ),
        "centerSmall": ParagraphStyle(
            "CenterSmall",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=TEXT,
            alignment=TA_CENTER,
        ),
    }


def _draw_header_footer(canvas, doc, report):
    styles = _build_styles()
    canvas.saveState()

    header_y = PAGE_HEIGHT - 20 * mm
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(1)
    canvas.line(LEFT_RIGHT_MARGIN, PAGE_HEIGHT - 34 * mm, PAGE_WIDTH - LEFT_RIGHT_MARGIN, PAGE_HEIGHT - 34 * mm)

    canvas.setFillColor(PRIMARY)
    canvas.circle(LEFT_RIGHT_MARGIN + 7 * mm, header_y + 1 * mm, 4 * mm, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawCentredString(LEFT_RIGHT_MARGIN + 7 * mm, header_y - 2, "+")

    title = Paragraph("SehatSaathi Clinic", styles["title"])
    kicker = Paragraph("CLINICAL CONSULTATION REPORT", styles["kicker"])
    title.wrapOn(canvas, 90 * mm, 10 * mm)
    kicker.wrapOn(canvas, 90 * mm, 10 * mm)
    title.drawOn(canvas, LEFT_RIGHT_MARGIN + 16 * mm, header_y - 3 * mm)
    kicker.drawOn(canvas, LEFT_RIGHT_MARGIN + 16 * mm, header_y - 10 * mm)

    now = datetime.now()
    meta_date = Paragraph(now.strftime("%d %b %Y"), styles["headerMeta"])
    meta_time = Paragraph(now.strftime("%I:%M %p"), styles["headerMeta"])
    meta_date.wrapOn(canvas, 35 * mm, 8 * mm)
    meta_time.wrapOn(canvas, 35 * mm, 8 * mm)
    meta_date.drawOn(canvas, PAGE_WIDTH - LEFT_RIGHT_MARGIN - 35 * mm, header_y - 1 * mm)
    meta_time.drawOn(canvas, PAGE_WIDTH - LEFT_RIGHT_MARGIN - 35 * mm, header_y - 8 * mm)

    footer_y = 16 * mm
    canvas.line(LEFT_RIGHT_MARGIN, footer_y + 20 * mm, PAGE_WIDTH - LEFT_RIGHT_MARGIN, footer_y + 20 * mm)

    footer_left = Paragraph("Generated by SehatSaathi", styles["footer"])
    footer_id = Paragraph(f"Report ID: {_stringify(report.get('report_id', report.get('id')))}", styles["footerMuted"])
    footer_left.wrapOn(canvas, 55 * mm, 8 * mm)
    footer_id.wrapOn(canvas, 55 * mm, 8 * mm)
    footer_left.drawOn(canvas, LEFT_RIGHT_MARGIN, footer_y + 10 * mm)
    footer_id.drawOn(canvas, LEFT_RIGHT_MARGIN, footer_y + 2 * mm)

    qr_x = PAGE_WIDTH - LEFT_RIGHT_MARGIN - 70 * mm
    canvas.setStrokeColor(BORDER)
    canvas.setFillColor(SURFACE_LOW)
    canvas.rect(qr_x, footer_y + 1 * mm, 18 * mm, 18 * mm, fill=1, stroke=1)
    canvas.setFillColor(SUBTEXT)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.drawCentredString(qr_x + 9 * mm, footer_y + 8 * mm, "QR")
    qr_label = Paragraph("Verification QR", styles["centerSmall"])
    qr_label.wrapOn(canvas, 25 * mm, 8 * mm)
    qr_label.drawOn(canvas, qr_x - 3 * mm, footer_y - 5 * mm)

    sign_x = PAGE_WIDTH - LEFT_RIGHT_MARGIN - 42 * mm
    canvas.setStrokeColor(TEXT)
    canvas.line(sign_x, footer_y + 10 * mm, PAGE_WIDTH - LEFT_RIGHT_MARGIN, footer_y + 10 * mm)
    sign_label = Paragraph("Clinic Signature Line", styles["centerSmall"])
    sign_name = Paragraph(f"Dr. {_stringify(report.get('doctor_name'))}", styles["footerMuted"])
    sign_label.wrapOn(canvas, 42 * mm, 8 * mm)
    sign_name.wrapOn(canvas, 42 * mm, 8 * mm)
    sign_label.drawOn(canvas, sign_x, footer_y + 1 * mm)
    sign_name.drawOn(canvas, sign_x, footer_y - 6 * mm)

    canvas.restoreState()


def _patient_details_table(report, styles):
    patient_rows = [
        [
            Paragraph("Patient Name", styles["label"]),
            Paragraph("Age / Gender", styles["label"]),
        ],
        [
            Paragraph(_stringify(report.get("patient_name")), styles["value"]),
            Paragraph(
                f"{_stringify(report.get('age'))} / {_stringify(report.get('gender'))}",
                styles["value"],
            ),
        ],
        [
            Paragraph("Consulting Doctor", styles["label"]),
            Paragraph("Patient ID", styles["label"]),
        ],
        [
            Paragraph(_stringify(report.get("doctor_name")), styles["value"]),
            Paragraph(_stringify(report.get("patient_id")), styles["value"]),
        ],
    ]
    table = Table(patient_rows, colWidths=[78 * mm, 78 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PRIMARY_LIGHT),
                ("BOX", (0, 0), (-1, -1), 1, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def _two_column_section(left_title, left_content, right_title, right_content, styles):
    table = Table(
        [
            [
                Paragraph(left_title, styles["section"]),
                Paragraph(right_title, styles["section"]),
            ],
            [left_content, right_content],
        ],
        colWidths=[78 * mm, 78 * mm],
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return table


def _bullet_paragraphs(items, styles):
    cleaned = _listify(items)
    if not cleaned:
        return Paragraph("No details available.", styles["body"])
    return [Paragraph(item, styles["bullet"], bulletText="•") for item in cleaned]


def _medications_table(report, styles):
    medications = _listify(report.get("medications"))
    dosage_entries = _listify(report.get("dosage"))

    rows = [
        [
            Paragraph("Medicine", styles["label"]),
            Paragraph("Dosage", styles["label"]),
            Paragraph("Timing", styles["label"]),
            Paragraph("Duration", styles["label"]),
        ]
    ]

    max_rows = max(len(medications), len(dosage_entries), 1)
    for index in range(max_rows):
        medicine = medications[index] if index < len(medications) else "Not specified"
        dosage, timing, duration = _split_dosage_entry(
            dosage_entries[index] if index < len(dosage_entries) else "As prescribed"
        )
        rows.append(
            [
                Paragraph(_stringify(medicine), styles["bodyDark"]),
                Paragraph(_stringify(dosage), styles["body"]),
                Paragraph(_stringify(timing), styles["body"]),
                Paragraph(_stringify(duration), styles["body"]),
            ]
        )

    table = Table(rows, colWidths=[50 * mm, 34 * mm, 34 * mm, 34 * mm], repeatRows=1)
    style_commands = [
        ("BACKGROUND", (0, 0), (-1, 0), SURFACE_LOW),
        ("BOX", (0, 0), (-1, -1), 1, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]

    for row_index in range(1, len(rows)):
        if row_index % 2 == 0:
            style_commands.append(("BACKGROUND", (0, row_index), (-1, row_index), BACKGROUND))

    table.setStyle(TableStyle(style_commands))
    return table


def generate_pdf(report: dict, output_file="clinical_report.pdf"):
    styles = _build_styles()
    doc = SimpleDocTemplate(
        output_file,
        pagesize=A4,
        leftMargin=LEFT_RIGHT_MARGIN,
        rightMargin=LEFT_RIGHT_MARGIN,
        topMargin=TOP_MARGIN,
        bottomMargin=BOTTOM_MARGIN,
        title="Clinical Consultation Report",
        author="SehatSaathi",
    )

    symptoms_content = _bullet_paragraphs(report.get("symptoms"), styles)
    diagnosis_content = Paragraph(_stringify(report.get("diagnosis")), styles["body"])
    precautions_content = _bullet_paragraphs(report.get("precautions"), styles)
    notes_content = Table(
        [[Paragraph(_stringify(report.get("doctor_notes")), styles["body"])]],
        colWidths=[78 * mm],
    )
    notes_content.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), SURFACE_LOW),
                ("BOX", (0, 0), (-1, -1), 1, BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 22),
            ]
        )
    )

    elements = [
        Paragraph("Patient Details", styles["section"]),
        _patient_details_table(report, styles),
        Spacer(1, 14),
        _two_column_section(
            "Symptoms",
            symptoms_content,
            "Diagnosis",
            diagnosis_content,
            styles,
        ),
        Spacer(1, 16),
        Paragraph("Medications", styles["section"]),
        _medications_table(report, styles),
        Spacer(1, 16),
        _two_column_section(
            "Precautions",
            precautions_content,
            "Doctor Notes",
            notes_content,
            styles,
        ),
    ]

    doc.build(
        elements,
        onFirstPage=lambda canvas, document: _draw_header_footer(canvas, document, report),
        onLaterPages=lambda canvas, document: _draw_header_footer(canvas, document, report),
    )

    return output_file
