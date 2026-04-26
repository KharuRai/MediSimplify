import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from typing import Dict, Any

def generate_simplified_pdf(data: Dict[str, Any], output_path: str):
    """
    Generates a PDF report using ReportLab based on the structured JSON data.
    """
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        alignment=TA_CENTER,
        spaceAfter=20
    )
    heading_style = styles['Heading2']
    body_style = styles['BodyText']
    
    story = []
    
    # Title
    story.append(Paragraph("Simplified Medical Report", title_style))
    
    # Disclaimer
    if "Disclaimer" in data:
        disclaimer_style = ParagraphStyle(
            'Disclaimer', parent=styles['Italic'], textColor='red', spaceAfter=15
        )
        story.append(Paragraph(data["Disclaimer"], disclaimer_style))
    
    # Medicines
    story.append(Paragraph("Medicines:", heading_style))
    if "Medicines" in data and isinstance(data["Medicines"], list) and len(data["Medicines"]) > 0:
        med_items = [ListItem(Paragraph(med, body_style)) for med in data["Medicines"]]
        story.append(ListFlowable(med_items, bulletType='bullet'))
    else:
        story.append(Paragraph("No medicines identified.", body_style))
    story.append(Spacer(1, 12))
    
    # Purpose
    story.append(Paragraph("Purpose:", heading_style))
    story.append(Paragraph(data.get("Purpose", "Not specified."), body_style))
    story.append(Spacer(1, 12))
    
    # Dosage
    story.append(Paragraph("Dosage Instructions:", heading_style))
    story.append(Paragraph(data.get("Dosage", "Not specified."), body_style))
    story.append(Spacer(1, 12))
    
    # Warnings
    story.append(Paragraph("Warnings & Side Effects:", heading_style))
    if "Warnings" in data and isinstance(data["Warnings"], list) and len(data["Warnings"]) > 0:
        warn_items = [ListItem(Paragraph(w, body_style)) for w in data["Warnings"]]
        story.append(ListFlowable(warn_items, bulletType='bullet'))
    else:
        story.append(Paragraph("No specific warnings identified.", body_style))
        
    doc.build(story)
