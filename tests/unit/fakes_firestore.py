"""In-memory Firestore stand-in for unit tests (mocked transactions)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable


class _Snap:
    def __init__(self, data: dict[str, Any] | None) -> None:
        self._data = data

    @property
    def exists(self) -> bool:
        return self._data is not None

    def to_dict(self) -> dict[str, Any] | None:
        return deepcopy(self._data) if self._data is not None else None


class _DocRef:
    def __init__(self, store: "FakeFirestore", path: str) -> None:
        self._store = store
        self.path = path

    def set(self, data: dict[str, Any]) -> None:
        self._store._docs[self.path] = deepcopy(data)

    def get(self, transaction: Any | None = None) -> _Snap:
        _ = transaction
        return _Snap(self._store._docs.get(self.path))


class _Query:
    def __init__(self, store: "FakeFirestore", collection: str, field: str, value: Any) -> None:
        self._store = store
        self._collection = collection
        self._field = field
        self._value = value

    def stream(self) -> list[_Snap]:
        prefix = f"{self._collection}/"
        out: list[_Snap] = []
        for path, data in self._store._docs.items():
            if path.startswith(prefix) and data.get(self._field) == self._value:
                out.append(_Snap(data))
        return out


class _Collection:
    def __init__(self, store: "FakeFirestore", name: str) -> None:
        self._store = store
        self.name = name

    def document(self, doc_id: str) -> _DocRef:
        return _DocRef(self._store, f"{self.name}/{doc_id}")

    def where(self, field: str, op: str, value: Any) -> _Query:
        assert op == "=="
        return _Query(self._store, self.name, field, value)

    def stream(self) -> list[_Snap]:
        prefix = f"{self.name}/"
        return [
            _Snap(data)
            for path, data in self._store._docs.items()
            if path.startswith(prefix)
        ]


class _Transaction:
    def __init__(self, store: "FakeFirestore") -> None:
        self._store = store
        self._writes: list[tuple[str, dict[str, Any]]] = []

    def set(self, ref: _DocRef, data: dict[str, Any]) -> None:
        self._writes.append((ref.path, deepcopy(data)))

    def commit(self) -> None:
        for path, data in self._writes:
            self._store._docs[path] = data
        self._writes.clear()


def transactional(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Minimal stand-in for google.cloud.firestore.transactional."""

    def wrapper(transaction: _Transaction, *args: Any, **kwargs: Any) -> Any:
        result = fn(transaction, *args, **kwargs)
        transaction.commit()
        return result

    return wrapper


class FakeFirestore:
    """Enough of the Firestore client surface for FirestoreStateStore unit tests."""

    SERVER_TIMESTAMP = "SERVER_TIMESTAMP"

    def __init__(self) -> None:
        self._docs: dict[str, dict[str, Any]] = {}

    def collection(self, name: str) -> _Collection:
        return _Collection(self, name)

    def transaction(self) -> _Transaction:
        return _Transaction(self)


class FakeFirestoreModule:
    SERVER_TIMESTAMP = FakeFirestore.SERVER_TIMESTAMP
    transactional = staticmethod(transactional)
