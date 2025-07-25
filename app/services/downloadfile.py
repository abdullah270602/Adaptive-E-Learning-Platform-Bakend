import io
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from docx import Document
from docx.shared import Inches

def create_pdf(mcqs: list) -> io.BytesIO:
    """
    Generate PDF from MCQ list
    Args:
        mcqs: List of MCQ dictionaries with 'question', 'options', 'correct_answer'
    Returns:
        io.BytesIO: PDF file buffer
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Add title
    story.append(Paragraph("Multiple Choice Questions", styles['Title']))
    story.append(Spacer(1, 20))
    
    # Add each MCQ
    for i, mcq in enumerate(mcqs, 1):
        # Question
        story.append(Paragraph(f"{i}. {mcq['question']}", styles['Heading2']))
        
        # Options
        for option in mcq['options']:
            story.append(Paragraph(f"   {option}", styles['Normal']))
        
        # Answer
        story.append(Paragraph(f"Answer: {mcq['correct_answer']}", styles['Normal']))
        story.append(Spacer(1, 15))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

def create_docx(mcqs: list) -> io.BytesIO:
    """
    Generate DOCX from MCQ list
    Args:
        mcqs: List of MCQ dictionaries with 'question', 'options', 'correct_answer'
    Returns:
        io.BytesIO: DOCX file buffer
    """
    doc = Document()
    
    # Add title
    doc.add_heading('Multiple Choice Questions', 0)
    
    # Add each MCQ
    for i, mcq in enumerate(mcqs, 1):
        # Question
        doc.add_heading(f"{i}. {mcq['question']}", level=2)
        
        # Options
        for option in mcq['options']:
            p = doc.add_paragraph(option)
            p.paragraph_format.left_indent = Inches(0.5)
        
        # Answer
        answer_p = doc.add_paragraph(f"Answer: {mcq['correct_answer']}")
        answer_p.runs[0].bold = True
        doc.add_paragraph()  # Add spacing
    
    # Save to buffer
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer