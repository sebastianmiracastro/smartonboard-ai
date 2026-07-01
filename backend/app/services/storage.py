"""Almacenamiento de los archivos subidos EN UN FOLDER del proyecto.

Los documentos que sube RR.HH. se guardan en `backend/uploads/<company_id>/<doc_id>.<ext>`
(un archivo por documento, organizado por empresa). Sirve para conservar el original
y poder reprocesarlo o re-verificarlo (fallback). En Docker, la carpeta se persiste
con un volumen (ver docker-compose.yml); en desarrollo el bind-mount ya la conserva
dentro del proyecto en la máquina.
"""
from pathlib import Path
from typing import Optional

# backend/app/services/storage.py -> parents[2] = backend
_BACKEND_DIR = Path(__file__).resolve().parents[2]
UPLOADS_DIR = _BACKEND_DIR / "uploads"


def save_document_file(company_id: str, doc_id: str, ext: str, file_bytes: bytes) -> str:
    """Guarda el archivo y devuelve su ruta RELATIVA (p. ej. 'uploads/comp-001/<id>.pdf')."""
    company_dir = UPLOADS_DIR / company_id
    company_dir.mkdir(parents=True, exist_ok=True)
    path = company_dir / f"{doc_id}.{ext or 'bin'}"
    path.write_bytes(file_bytes)
    return str(path.relative_to(_BACKEND_DIR)).replace("\\", "/")


def read_document_file(rel_path: Optional[str]) -> Optional[bytes]:
    """Lee el archivo guardado a partir de su ruta relativa. None si no existe."""
    if not rel_path:
        return None
    path = _BACKEND_DIR / rel_path
    return path.read_bytes() if path.exists() else None


def delete_document_file(rel_path: Optional[str]) -> None:
    """Borra el archivo del folder (si existe). No falla si ya no está."""
    if not rel_path:
        return
    path = _BACKEND_DIR / rel_path
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass
