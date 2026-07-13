from pathlib import Path
import pdfplumber
from docx import Document


def extract_text_from_pdf(path):
    text = []

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()

            if page_text:
                text.append(page_text)

    return "\n".join(text).strip()


def extract_text_from_docx(path):
    doc = Document(path)

    paragraphs = [
        p.text.strip()
        for p in doc.paragraphs
        if p.text.strip()
    ]

    return "\n".join(paragraphs)


def extract_text_from_txt(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except UnicodeDecodeError:
        with open(path, "r", encoding="latin-1") as f:
            return f.read().strip()


def load_document(path):
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    suffix = path.suffix.lower()

    if suffix == ".pdf":
        text = extract_text_from_pdf(path)

    elif suffix == ".docx":
        text = extract_text_from_docx(path)

    elif suffix == ".txt":
        text = extract_text_from_txt(path)

    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    if not text.strip():
        raise ValueError(f"No readable text found in {path.name}")

    return text