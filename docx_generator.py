import tempfile

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt


def _apply_paragraph_font(paragraph) -> None:
    for run in paragraph.runs:
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)


def generate_docx(formatted_text: str, session_label: str = "") -> str:
    if not formatted_text.strip():
        raise ValueError("Formatted text is empty")

    doc = Document()

    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1.25)
        section.right_margin = Inches(1.25)

    if session_label:
        title = doc.add_heading(session_label, level=1)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    for line in formatted_text.splitlines():
        clean_line = line.strip()
        if not clean_line:
            continue

        paragraph = doc.add_paragraph(clean_line)
        _apply_paragraph_font(paragraph)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
    tmp.close()
    doc.save(tmp.name)
    return tmp.name
