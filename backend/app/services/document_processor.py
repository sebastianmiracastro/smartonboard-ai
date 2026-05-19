import io
import re
from typing import List
from pypdf import PdfReader
from docx import Document as DocxDocument

def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def extract_text_from_docx(file_bytes: bytes) -> str:
    doc = DocxDocument(io.BytesIO(file_bytes))
    text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    return text

def extract_text_from_txt(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8", errors="ignore")

def extract_text(file_bytes: bytes, format: str) -> str:
    if format == "pdf":
        return extract_text_from_pdf(file_bytes)
    elif format == "docx":
        return extract_text_from_docx(file_bytes)
    elif format == "txt":
        return extract_text_from_txt(file_bytes)
    return ""

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    # Limpiar texto
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r' +', ' ', text)
    text = text.strip()

    if not text:
        return []

    # Dividir por oraciones primero
    sentences = re.split(r'(?<=[.!?])\s+', text)

    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= chunk_size:
            current_chunk += " " + sentence
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            # Overlap: incluir últimas palabras del chunk anterior
            words = current_chunk.split()
            overlap_text = " ".join(words[-overlap:]) if len(words) > overlap else ""
            current_chunk = overlap_text + " " + sentence

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks