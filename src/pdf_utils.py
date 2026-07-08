"""PDF utilities: export study guide as PDF, extract text from uploaded PDFs."""

import re
import os
import platform
from io import BytesIO
from fpdf import FPDF
import pypdf

# Emoji + extended Unicode pattern to strip out of PDF text
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F" "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF" "\U0001F1E0-\U0001F1FF"
    "\U0001F900-\U0001F9FF" "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF" "\u2702-\u27B0"
    "\u2600-\u26FF" "\u2B50\u2934\u2935\u25AA\u25AB"
    "\u25FB\u25FC\u25FD\u25FE" "\uFE00-\uFE0F" "\u200D"
    "]+",
    re.UNICODE,
)


def _find_font():
    candidates = []
    if platform.system() == "Windows":
        candidates = [
            ("C:\\Windows\\Fonts\\arial.ttf", "C:\\Windows\\Fonts\\arialbd.ttf"),
        ]
    elif platform.system() == "Linux":
        candidates = [
            ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
            ("/usr/share/fonts/TTF/DejaVuSans.ttf", "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"),
        ]
    for regular, bold in candidates:
        if os.path.exists(regular) and os.path.exists(bold):
            return regular, bold
    return None, None


FONT_PATH, FONT_BOLD_PATH = _find_font()
USE_CUSTOM_FONT = FONT_PATH is not None


def _clean(text: str) -> str:
    text = EMOJI_PATTERN.sub("", text)
    text = re.sub(r"\*\*", "", text)
    return text


def export_pdf(topic: str, guide: str) -> BytesIO:
    pdf = FPDF()
    pdf.add_page()
    family = "Helvetica"
    if USE_CUSTOM_FONT:
        pdf.add_font("CustomFont", "", FONT_PATH, uni=True)
        pdf.add_font("CustomFont", "B", FONT_BOLD_PATH, uni=True)
        family = "CustomFont"
    pdf.set_font(family, "B", 20)
    pdf.multi_cell(0, 12, _clean(f"Study Guide: {topic}"))
    pdf.ln(5)
    pdf.set_font(family, "", 11)

    for line in guide.split("\n"):
        stripped = _clean(line.strip())
        if not stripped:
            pdf.ln(3)
            continue
        if stripped.startswith("#"):
            pdf.ln(2)
            pdf.set_font(family, "B", 14)
            pdf.multi_cell(0, 8, stripped.lstrip("#").strip())
            pdf.set_font(family, "", 11)
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
