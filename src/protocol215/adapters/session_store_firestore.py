"""Firestore-backed ADK SessionService — durable across worker restarts."""

from __future__ import annotations

import time
import uuid
from typing import Any, override

from google.adk.events.event import Event
from google.adk.sessions.base_session_service import (
    BaseSessionService,
    GetSessionConfig,
    ListSessionsResponse,
)
from google.adk.sessions.session import Session


class FirestoreSessionService(BaseSessionService):
    """
    Persist ADK sessions and events in Firestore.

    Collections:
      adk_sessions/{app_name}__{user_id}__{session_id}
      adk_events/{app_name}__{user_id}__{session_id}__{event_id}
      adk_user_states/{app_name}__{user_id}
      adk_app_states/{app_name}
    """

    def __init__(self, *, project: str | None = None, client: Any | None = None) -> None:
        if client is not None:
            self._db = client
        else:
            from google.cloud import firestore

            self._db = firestore.Client(project=project)

    def _session_doc_id(self, app_name: str, user_id: str, session_id: str) -> str:
        return f"{app_name}__{user_id}__{session_id}"

    def _event_doc_id(self, app_name: str, user_id: str, session_id: str, event_id: str) -> str:
        return f"{app_name}__{user_id}__{session_id}__{event_id}"

    @override
    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        state: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> Session:
        sid = (session_id or "").strip() or str(uuid.uuid4())
        now = time.time()
        session_state = dict(state or {})
        doc_id = self._session_doc_id(app_name, user_id, sid)
        ref = self._db.collection("adk_sessions").document(doc_id)
        if ref.get().exists:
            raise RuntimeError(f"Session with id {sid} already exists.")
        ref.set(
            {
                "app_name": app_name,
                "user_id": user_id,
                "id": sid,
                "state": session_state,
                "create_time": now,
                "update_time": now,
            }
        )
        return Session(
            app_name=app_name,
            user_id=user_id,
            id=sid,
            state=session_state,
            events=[],
            last_update_time=now,
        )

    @override
    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: GetSessionConfig | None = None,
    ) -> Session | None:
        doc = (
            self._db.collection("adk_sessions")
            .document(self._session_doc_id(app_name, user_id, session_id))
            .get()
        )
        if not doc.exists:
            return None
        data = doc.to_dict() or {}
        events_query = (
            self._db.collection("adk_events")
            .where("app_name", "==", app_name)
            .where("user_id", "==", user_id)
            .where("session_id", "==", session_id)
            .order_by("timestamp")
        )
        event_docs = list(events_query.stream())
        events: list[Event] = []
        for ed in event_docs:
            edata = ed.to_dict() or {}
            if (
                config is not None
                and config.after_timestamp is not None
                and float(edata.get("timestamp", 0)) < config.after_timestamp
            ):
                continue
            raw = edata.get("event_data")
            if isinstance(raw, str):
                events.append(Event.model_validate_json(raw))
            elif isinstance(raw, dict):
                events.append(Event.model_validate(raw))
        if config and config.num_recent_events is not None:
            events = [] if config.num_recent_events == 0 else events[-config.num_recent_events :]
        return Session(
            app_name=app_name,
            user_id=user_id,
            id=session_id,
            state=dict(data.get("state") or {}),
            events=events,
            last_update_time=float(data.get("update_time") or time.time()),
        )

    @override
    async def list_sessions(
        self, *, app_name: str, user_id: str | None = None
    ) -> ListSessionsResponse:
        q = self._db.collection("adk_sessions").where("app_name", "==", app_name)
        if user_id is not None:
            q = q.where("user_id", "==", user_id)
        sessions: list[Session] = []
        for doc in q.stream():
            data = doc.to_dict() or {}
            sessions.append(
                Session(
                    app_name=app_name,
                    user_id=str(data.get("user_id") or ""),
                    id=str(data.get("id") or ""),
                    state={},
                    events=[],
                    last_update_time=float(data.get("update_time") or 0),
                )
            )
        return ListSessionsResponse(sessions=sessions)

    @override
    async def delete_session(self, *, app_name: str, user_id: str, session_id: str) -> None:
        self._db.collection("adk_sessions").document(
            self._session_doc_id(app_name, user_id, session_id)
        ).delete()
        for ed in (
            self._db.collection("adk_events")
            .where("app_name", "==", app_name)
            .where("user_id", "==", user_id)
            .where("session_id", "==", session_id)
            .stream()
        ):
            ed.reference.delete()

    @override
    async def append_event(self, session: Session, event: Event) -> Event:
        now = time.time()
        event_id = event.id or str(uuid.uuid4())
        if not event.id:
            event = event.model_copy(update={"id": event_id})
        ts = float(getattr(event, "timestamp", None) or now)
        self._db.collection("adk_events").document(
            self._event_doc_id(session.app_name, session.user_id, session.id, event_id)
        ).set(
            {
                "app_name": session.app_name,
                "user_id": session.user_id,
                "session_id": session.id,
                "id": event_id,
                "invocation_id": getattr(event, "invocation_id", "") or "",
                "timestamp": ts,
                "event_data": event.model_dump_json(),
            }
        )
        # Persist session state updates if present on the event.
        state_delta = getattr(event, "actions", None)
        session_state = dict(session.state or {})
        if state_delta is not None and getattr(state_delta, "state_delta", None):
            session_state.update(state_delta.state_delta or {})
            session.state = session_state
        self._db.collection("adk_sessions").document(
            self._session_doc_id(session.app_name, session.user_id, session.id)
        ).set(
            {
                "app_name": session.app_name,
                "user_id": session.user_id,
                "id": session.id,
                "state": session_state,
                "update_time": now,
            },
            merge=True,
        )
        session.events.append(event)
        session.last_update_time = now
        return event

    @override
    async def get_user_state(self, *, app_name: str, user_id: str) -> dict[str, Any]:
        doc = self._db.collection("adk_user_states").document(f"{app_name}__{user_id}").get()
        if not doc.exists:
            return {}
        return dict((doc.to_dict() or {}).get("state") or {})
