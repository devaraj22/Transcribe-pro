import os
import uuid
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from backend.app.core.config import settings

def generate_pdf_report(title: str, summary: str, action_items: list[str], full_text: str) -> str:
    """
    Compiles the AI-generated data into a clean, structured PDF report.
    Returns the file path of the saved PDF.
    """
    # Ensure the reports directory exists
    os.makedirs(settings.REPORT_DIR, exist_ok=True)
    
    # Generate a unique filename
    filename = f"Meeting_Report_{uuid.uuid4().hex[:8]}.pdf"
    file_path = os.path.join(settings.REPORT_DIR, filename)
    
    # Setup the PDF document
    doc = SimpleDocTemplate(file_path, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Create custom styles
    title_style = styles['Heading1']
    heading_style = styles['Heading2']
    body_style = styles['BodyText']
    bullet_style = ParagraphStyle(
        "Bullet",
        parent=styles['BodyText'],
        leftIndent=20,
        spaceAfter=5
    )
    
    # Build the document story (the sequence of elements)
    story = []
    
    # 1. Title
    story.append(Paragraph(title if title else "Meeting Transcript & AI Report", title_style))
    story.append(Spacer(1, 12))
    
    # 2. Executive Summary
    if summary:
        story.append(Paragraph("Executive Summary", heading_style))
        story.append(Paragraph(summary, body_style))
        story.append(Spacer(1, 12))
        
    # 3. Action Items
    if action_items:
        story.append(Paragraph("Action Items", heading_style))
        for item in action_items:
            story.append(Paragraph(f"• {item}", bullet_style))
        story.append(Spacer(1, 12))
        
    # 4. Full Transcript
    if full_text:
        story.append(Paragraph("Full Transcript", heading_style))
        story.append(Paragraph(full_text, body_style))
        
    # Compile and save the PDF
    doc.build(story)
    
    return file_path