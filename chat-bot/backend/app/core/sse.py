import json
from collections.abc import Iterator


def encode(event: str, data: dict | str) -> str:
    payload = data if isinstance(data, str) else json.dumps(data, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


def stream_text(text: str, chunk: int = 24) -> Iterator[str]:
    for index in range(0, len(text), chunk):
        yield encode("token", {"text": text[index : index + chunk]})
