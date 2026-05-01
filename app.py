# pdf_service.py

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors
import os

# Fixed output directory
OUTPUT_DIR = r"C:\Users\Chait\Downloads\Desktop\SehatSaathi_v2\Services\output"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def generate_pdf(report: dict, filename="clinical_report.pdf"):
    file_path = os.path.join(OUTPUT_DIR, filename)

    styles = getSampleStyleSheet()
    elements = []

    # Header
    elements.append(Paragraph("SehatSaathi Clinic", styles['Title']))
    elements.append(Paragraph("Clinical Consultation Report", styles['Heading2']))
    elements.append(Spacer(1, 20))

    # Patient Info Table
    patient_info = [
        ["Patient Name", str(report.get("patient_name"))],
        ["Age", str(report.get("age"))],
        ["Gender", str(report.get("gender"))]
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

    # Doctor Notes
    elements.append(Paragraph("Doctor Notes", styles['Heading3']))
    elements.append(Paragraph(str(report.get("doctor_notes")), styles['Normal']))
    elements.append(Spacer(1, 30))

    # Signature
    elements.append(Paragraph("Doctor Signature: ____________________", styles['Normal']))

    # Build PDF
    doc = SimpleDocTemplate(file_path)
    doc.build(elements)

    return file_path

if __name__ == "__main__":
    print("Running PDF test...")

    sample = {
        "patient_name": "Test Patient",
        "age": 25,
        "gender": "Male",
        "symptoms": ["Fever", "Cough"],
        "diagnosis": "Viral Infection",
        "medications": ["Paracetamol"],
        "dosage": ["500 mg twice daily"],
        "precautions": ["Rest", "Hydration"],
        "doctor_notes": "Follow up in 3 days"
    }

    path = generate_pdf(sample, "test_report.pdf")

    print("PDF generated at:", path)