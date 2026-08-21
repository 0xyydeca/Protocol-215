"""Hashing helpers for audit integrity and idempotency."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def sha256_hex(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def hash_payload(payload: Any) -> str:
    return sha256_hex(canonical_json(payload if payload is not None else {}))


GENESIS_HASH = "0" * 64


def build_idempotency_key(
    *,
    run_id: str,
    action_type: str,
    target_id: str,
    protocol_version: str,
) -> str:
    return f"{run_id}:{action_type}:{target_id}:{protocol_version}"
