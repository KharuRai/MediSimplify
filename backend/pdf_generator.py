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
    disclaimer_text = data.get("Disclaimer", None)
    if disclaimer_text:
        disclaimer_style = ParagraphStyle(
            'Disclaimer', parent=styles['Italic'], textColor='red', spaceAfter=15
        )
        story.append(Paragraph(disclaimer_text, disclaimer_style))
    
    # Dynamically render sections based on data keys
    for key, value in data.items():
        if not value or key == "Disclaimer":
            continue
            
        story.append(Paragraph(f"{key}:", heading_style))
        
        if isinstance(value, str):
            story.append(Paragraph(value, body_style))
        elif isinstance(value, list) and len(value) > 0:
            if isinstance(value[0], dict):
                # Handle Lab Results (list of dicts)
                dict_items = []
                for item in value:
                    item_str = ", ".join([f"{k}: {v}" for k, v in item.items() if v is not None])
                    dict_items.append(ListItem(Paragraph(item_str, body_style)))
                story.append(ListFlowable(dict_items, bulletType='bullet'))
            else:
                # Handle simple list of strings
                list_items = [ListItem(Paragraph(str(v), body_style)) for v in value]
                story.append(ListFlowable(list_items, bulletType='bullet'))
        else:
            story.append(Paragraph(str(value), body_style))
            
        story.append(Spacer(1, 12))
        
    doc.build(story)
