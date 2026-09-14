"""Deterministic cache-key helpers for generated media."""

import hashlib
import json
from typing import Mapping


def cache_key(namespace: str, values: Mapping[str, object]) -> str:
    """Return a stable SHA-256 key for a generation request and its inputs."""
    if not namespace:
        raise ValueError("cache namespace must not be empty")
    payload = json.dumps(
        {"namespace": namespace, "values": values},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
