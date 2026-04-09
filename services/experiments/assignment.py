"""Deterministic user-to-variant assignment via HMAC-SHA256."""
from __future__ import annotations

import hashlib
import hmac


def assign_variant(
    user_id: str,
    experiment_id: str,
    variants: list[dict],
    traffic_split: dict[str, float],
) -> str:
    key = f"{experiment_id}:{user_id}".encode()
    digest = hmac.new(b"converta-salt", key, hashlib.sha256).digest()
    bucket = int.from_bytes(digest[:4], "big") / (2**32)

    cumulative = 0.0
    for variant in variants:
        vid = variant["id"]
        share = traffic_split.get(vid, 0.0)
        cumulative += share
        if bucket < cumulative:
            return vid

    return variants[-1]["id"]
