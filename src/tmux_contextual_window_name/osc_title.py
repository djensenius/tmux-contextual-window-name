from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizedTitle:
    raw: str
    current_intent: str | None
    is_copilot: bool
    is_idle: bool


def normalize_title(title: str | None, session_name: str | None = None) -> NormalizedTitle:
    raw = (title or "").strip()
    session = (session_name or "").strip()

    if not raw:
        return NormalizedTitle(raw=raw, current_intent=None, is_copilot=False, is_idle=True)

    for prefix in ("🤖 ", "Copilot: "):
        if raw.startswith(prefix):
            intent = raw[len(prefix) :].strip()
            return NormalizedTitle(
                raw=raw,
                current_intent=intent or None,
                is_copilot=True,
                is_idle=not bool(intent),
            )

    if raw == "GitHub Copilot" or (session and raw == session):
        return NormalizedTitle(raw=raw, current_intent=None, is_copilot=True, is_idle=True)

    return NormalizedTitle(raw=raw, current_intent=None, is_copilot=False, is_idle=False)
