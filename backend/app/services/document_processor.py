import io
import re
from typing import List
from pypdf import PdfReader
from docx import Document as DocxDocument

# Parámetros de fragmentación (contextos coherentes, no fragmentos arbitrarios)
DEFAULT_CHUNK_SIZE = 800      # tamaño objetivo del contexto en caracteres
DEFAULT_OVERLAP = 120         # solape entre contextos (continuidad), recortado a palabra
MIN_CHUNK_LEN = 40            # descarta fragmentos demasiado cortos (encabezados, ruido)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    # Se separan las páginas con doble salto para conservar el límite de párrafo
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n\n".join(parts)


def extract_text_from_docx(file_bytes: bytes) -> str:
    doc = DocxDocument(io.BytesIO(file_bytes))
    # Cada párrafo no vacío en su propia línea; los vacíos marcan separación
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


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


# ─── LIMPIEZA Y FRAGMENTACIÓN ────────────────────────────────────────────────

def _clean(text: str) -> str:
    """Normaliza el texto preservando los límites de párrafo."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Une palabras cortadas por guion al final de línea: "infor-\nmación" -> "información"
    text = re.sub(r"-\n(\w)", r"\1", text)
    # Espacios/tabs múltiples -> uno solo (sin tocar los saltos de línea)
    text = re.sub(r"[ \t]+", " ", text)
    # Más de un salto -> separación de párrafo
    text = re.sub(r"\n{2,}", "\n\n", text)
    return text.strip()


def _split_sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _trim_to_word(tail: str) -> str:
    """Recorta el solape para que empiece en una palabra completa."""
    tail = tail.lstrip()
    sp = tail.find(" ")
    return tail[sp + 1:] if sp != -1 else tail


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
    min_len: int = MIN_CHUNK_LEN,
) -> List[str]:
    """Divide el texto en contextos coherentes.

    Estrategia: párrafos como unidad básica; los párrafos muy largos se parten por
    oraciones; las unidades se agrupan hasta `chunk_size` con un pequeño solape para
    no cortar ideas a la mitad. Así el agente recupera CONTEXTOS, no trozos sueltos.
    """
    text = _clean(text)
    if not text:
        return []

    # 1) Unidades: párrafos; los grandes se sub-dividen por oraciones
    units: List[str] = []
    for para in re.split(r"\n{2,}", text):
        para = re.sub(r"\s+", " ", para).strip()
        if not para:
            continue
        if len(para) <= chunk_size:
            units.append(para)
        else:
            acc = ""
            for sent in _split_sentences(para):
                if len(sent) > chunk_size:
                    # Oración monstruo: trocear por longitud como último recurso
                    if acc:
                        units.append(acc)
                        acc = ""
                    for i in range(0, len(sent), chunk_size):
                        units.append(sent[i:i + chunk_size])
                elif len(acc) + len(sent) + 1 <= chunk_size:
                    acc = (acc + " " + sent).strip()
                else:
                    if acc:
                        units.append(acc)
                    acc = sent
            if acc:
                units.append(acc)

    # 2) Agrupar unidades en contextos con solape por caracteres (recortado a palabra)
    chunks: List[str] = []
    current = ""
    for u in units:
        if not current:
            current = u
        elif len(current) + len(u) + 1 <= chunk_size:
            current = current + " " + u
        else:
            chunks.append(current.strip())
            tail = _trim_to_word(current[-overlap:]) if overlap > 0 else ""
            current = (tail + " " + u).strip() if tail else u
    if current.strip():
        chunks.append(current.strip())

    # 3) Descartar ruido (fragmentos demasiado cortos)
    return [c for c in chunks if len(c) >= min_len]
