"""PDF utilities: export study guide as PDF, extract text from uploaded PDFs."""

from io import BytesIO
from fpdf import FPDF
import pypdf

FONT_PATH = "C:\\Windows\\Fonts\\arial.ttf"
FONT_BOLD_PATH = "C:\\Windows\\Fonts\\arialbd.ttf"


def export_pdf(topic: str, guide: str) -> BytesIO:
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("Arial", "", FONT_PATH, uni=True)
    pdf.add_font("Arial", "B", FONT_BOLD_PATH, uni=True)
    pdf.set_font("Arial", "B", 20)
    pdf.multi_cell(0, 12, f"Study Guide: {topic}")
    pdf.ln(5)
    pdf.set_font("Arial", "", 11)

    for line in guide.split("\n"):
        stripped = line.strip()
        if not stripped:
            pdf.ln(3)
            continue
        if stripped.startswith("##") or stripped.startswith("###"):
            pdf.ln(2)
            pdf.set_font("Arial", "B", 14)
            pdf.multi_cell(0, 8, stripped.lstrip("#").strip())
            pdf.set_font("Arial", "", 11)
        elif stripped.startswith("**") and stripped.endswith("**"):
            pdf.set_font("Arial", "B", 11)
            pdf.multi_cell(0, 7, stripped.strip("*"))
            pdf.set_font("Arial", "", 11)
        else:
            pdf.multi_cell(0, 6, stripped)

    buf = BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return buf


def extract_text_from_pdf(file_bytes: bytes) -> str:
    text = []
    reader = pypdf.PdfReader(BytesIO(file_bytes))
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text.append(page_text)
    return "\n".join(text)
