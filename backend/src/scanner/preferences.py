from __future__ import annotations

from typing import Iterable, List


def normalize_extensions(values: Iterable[str] | None) -> List[str]:
    """
    Normalize extension strings so downstream filters always use the
    canonical ``.ext`` form and duplicate values are removed.
    """
    normalized: List[str] = []
    seen: set[str] = set()

    if not values:
        return normalized

    for raw in values:
        if not isinstance(raw, str):
            continue
        token = raw.strip().lower()
        if not token:
            continue
        if not token.startswith("."):
            token = f".{token}"
        if token not in seen:
            seen.add(token)
            normalized.append(token)

    return normalized
