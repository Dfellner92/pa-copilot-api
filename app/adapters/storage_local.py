import os, uuid
from pathlib import Path
from typing import BinaryIO
from app.core.config import settings

BASE = Path(settings.file_storage_dir)

def ensure_dir() -> None:
    BASE.mkdir(parents=True, exist_ok=True)

def save_file(stream: BinaryIO, content_type: str, original_name: str) -> tuple[str, int]:
    """
    Saves to local disk under a UUID filename. Returns (storage_key, size_bytes).
    """
    ensure_dir()
    storage_key = f"{uuid.uuid4().hex}"
    out_path = BASE / storage_key
    size = 0
    with open(out_path, "wb") as f:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            f.write(chunk)
    return storage_key, size

def open_file(storage_key: str) -> BinaryIO:
    path = BASE / storage_key
    return open(path, "rb")

def exists(storage_key: str) -> bool:
    return (BASE / storage_key).exists()
