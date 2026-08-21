"""Identifier generators."""

from __future__ import annotations

import itertools
import uuid


class UUIDIdentifierGenerator:
    def new_id(self, prefix: str = "") -> str:
        value = str(uuid.uuid4())
        return f"{prefix}{value}" if prefix else value


class DeterministicIdentifierGenerator:
    def __init__(self, prefix: str = "id") -> None:
        self._counter = itertools.count(1)
        self._prefix = prefix

    def new_id(self, prefix: str = "") -> str:
        n = next(self._counter)
        stem = prefix or self._prefix
        return f"{stem}-{n:04d}"
