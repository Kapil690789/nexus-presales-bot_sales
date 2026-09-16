from pathlib import Path
from uuid import uuid4

from backend.app.core.settings import get_settings


def store_bytes(filename: str, data: bytes) -> str:
    settings = get_settings()
    safe_name = f"{uuid4().hex}_{Path(filename).name}"
    if settings.gcs_bucket:
        from google.cloud import storage

        blob = storage.Client().bucket(settings.gcs_bucket).blob(f"{settings.gcs_prefix}{safe_name}")
        blob.upload_from_string(data)
        return f"gs://{settings.gcs_bucket}/{settings.gcs_prefix}{safe_name}"
    directory = Path(settings.upload_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / safe_name
    path.write_bytes(data)
    return str(path)
