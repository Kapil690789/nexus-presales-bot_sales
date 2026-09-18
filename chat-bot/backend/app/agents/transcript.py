from __future__ import annotations

from typing import Any, Iterable

MAX_TURNS = 16
MAX_CHARS = 6000


def render_transcript(
    messages: Iterable[Any],
    *,
    max_turns: int = MAX_TURNS,
    max_chars: int = MAX_CHARS,
) -> str:
    """Flatten session messages for the model. Newest turns are kept when capping."""
    lines: list[str] = []
    for message in messages:
        role = _attr(message, "role")
        content = (_attr(message, "content") or "").strip()
        if not role or not content:
            continue
        lines.append(f"{role}: {content}")
    if len(lines) > max_turns:
        lines = lines[-max_turns:]
    text = "\n".join(lines)
    if len(text) > max_chars:
        text = text[-max_chars:]
        cut = text.find("\n")
        if cut != -1:
            text = text[cut + 1 :]
    return text.strip()


def _attr(message: Any, name: str) -> str:
    if isinstance(message, dict):
        return str(message.get(name) or "")
    return str(getattr(message, name, "") or "")
