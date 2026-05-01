# pdf_service.py

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors
import os

def generate_pdf(report: dict, output_file="clinical_report.pdf"):
    
    styles = getSampleStyleSheet()
    elements = []

    # Header
    elements.append(Paragraph("SehatSaathi Clinic", styles['Title']))
    elements.append(Paragraph("Clinical Consultation Report", styles['Heading2']))
    elements.append(Spacer(1, 20))

    # Patient Info Table
    patient_info = [
        ["Patient Name", report.get("patient_name")],
        ["Age", report.get("age")],
        ["Gender", report.get("gender")]
    ]

    table = Table(patient_info, colWidths=[2*inch, 4*inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,-1), colors.lightgrey),
        ("GRID", (0,0), (-1,-1), 1, colors.grey)
    ]))

    elements.append(Paragraph("Patient Information", styles['Heading3']))
    elements.append(table)
    elements.append(Spacer(1, 20))

    # Symptoms
    elements.append(Paragraph("Symptoms", styles['Heading3']))
    for s in report.get("symptoms", []):
        elements.append(Paragraph(f"- {s}", styles['Normal']))
    elements.append(Spacer(1, 15))

    # Diagnosis
    elements.append(Paragraph("Diagnosis", styles['Heading3']))
    elements.append(Paragraph(str(report.get("diagnosis")), styles['Normal']))
    elements.append(Spacer(1, 15))

    # Medications
    elements.append(Paragraph("Medications", styles['Heading3']))
    for m in report.get("medications", []):
        elements.append(Paragraph(f"- {m}", styles['Normal']))
    elements.append(Spacer(1, 15))

    # Dosage
    elements.append(Paragraph("Dosage", styles['Heading3']))
    for d in report.get("dosage", []):
        elements.append(Paragraph(f"- {d}", styles['Normal']))
    elements.append(Spacer(1, 15))

    # Precautions
    elements.append(Paragraph("Precautions", styles['Heading3']))
    for p in report.get("precautions", []):
        elements.append(Paragraph(f"- {p}", styles['Normal']))
    elements.append(Spacer(1, 15))

    # Notes
    elements.append(Paragraph("Doctor Notes", styles['Heading3']))
    elements.append(Paragraph(str(report.get("doctor_notes")), styles['Normal']))
    elements.append(Spacer(1, 30))

    # Signature
    elements.append(Paragraph("Doctor Signature: ____________________", styles['Normal']))

    # Generate PDF
    doc = SimpleDocTemplate(output_file)
    doc.build(elements)

    return output_file