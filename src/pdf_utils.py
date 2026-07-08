"""PDF utilities: export study guide as PDF, extract text from uploaded PDFs."""

import re
from io import BytesIO
from fpdf import FPDF
import pypdf

FONT_PATH = "C:\\Windows\\Fonts\\arial.ttf"
FONT_BOLD_PATH = "C:\\Windows\\Fonts\\arialbd.ttf"

# Emoji + extended Unicode pattern to strip out of PDF text
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U0001FA00-\U0001FA6F"  # chess symbols
    "\U0001FA70-\U0001FAFF"  # symbols extended-A
    "\u2702-\u27B0"          # dingbats
    "\u2600-\u26FF"          # misc symbols
    "\u2B50\u2934\u2935\u25AA\u25AB\u25FB\u25FC\u25FD\u25FE"
    "\uFE00-\uFE0F"          # variation selectors
    "\u200D"                 # zero-width joiner
    "]+",
    re.UNICODE,
)


def _clean(text: str) -> str:
    text = EMOJI_PATTERN.sub("", text)
    text = re.sub(r"\*\*", "", text)
    return text


def export_pdf(topic: str, guide: str) -> BytesIO:
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("Arial", "", FONT_PATH, uni=True)
    pdf.add_font("Arial", "B", FONT_BOLD_PATH, uni=True)
    pdf.set_font("Arial", "B", 20)
    pdf.multi_cell(0, 12, _clean(f"Study Guide: {topic}"))
    pdf.ln(5)
    pdf.set_font("Arial", "", 11)

    for line in guide.split("\n"):
        stripped = _clean(line.strip())
        if not stripped:
            pdf.ln(3)
            continue
        if stripped.startswith("#"):
            pdf.ln(2)
            pdf.set_font("Arial", "B", 14)
            pdf.multi_cell(0, 8, stripped.lstrip("#").strip())
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
