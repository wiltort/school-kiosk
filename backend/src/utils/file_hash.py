import hashlib
from pathlib import Path


def get_file_hash(file_path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()
