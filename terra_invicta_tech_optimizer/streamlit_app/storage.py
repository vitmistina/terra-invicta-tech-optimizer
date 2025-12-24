from __future__ import annotations

import json

import streamlit as st
from streamlit_local_storage import LocalStorage

from terra_invicta_tech_optimizer import BacklogState, DecodedBacklog, GraphData, decode_backlog, encode_backlog
from terra_invicta_tech_optimizer.backlog_storage import STORAGE_KEY


def _get_local_storage() -> LocalStorage:
    manager = st.session_state.get("local_storage_manager")
    if manager is None:
        manager = LocalStorage()
        st.session_state.local_storage_manager = manager
    return manager


def _read_backlog_storage() -> tuple[dict | None, str | None]:
    st.session_state.setdefault("backlog_storage_attempts", 0)

    # Avoid spawning additional background iframes once we've tried a few times.
    if st.session_state.backlog_storage_attempts > 3:
        return None, None

    st.session_state.backlog_storage_attempts += 1
    storage = _get_local_storage()
    try:
        raw = storage.getItem(STORAGE_KEY)
    except Exception as exc:  # pragma: no cover - defensive for component failures.
        return None, str(exc)

    if raw is None:
        return None, None
    if isinstance(raw, dict):
        return raw, None
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            return None, str(exc)
        return parsed, None
    return None, f"Unexpected local storage payload type: {type(raw).__name__}"


def _write_backlog_storage(payload: dict) -> None:
    payload_json = json.dumps(payload)
    st.components.v1.html(
        f"""
        <script>
        (() => {{
          try {{
            const payload = {payload_json};
            window.localStorage.setItem("{STORAGE_KEY}", JSON.stringify(payload));
          }} catch (err) {{
            console.warn("Failed to persist backlog to localStorage", err);
          }}
        }})();
        </script>
        """,
        height=0,
        width=0,
    )


def hydrate_backlog_from_storage(graph_data: GraphData) -> DecodedBacklog | None:
    if st.session_state.get("backlog_storage_hydrated"):
        return None

    payload, error = _read_backlog_storage()
    if error:
        st.session_state.backlog_storage_read_error = error
    if payload is None:
        st.session_state.backlog_storage_hydrated = True
        return None

    decoded = decode_backlog(payload, graph_data)
    if decoded:
        st.session_state.backlog_state = decoded.backlog
        st.session_state.backlog_storage_hydrated = True
        st.session_state.backlog_storage_last = json.dumps(payload, sort_keys=True)
        st.session_state.backlog_storage_last_order = decoded.backlog.order
        st.session_state.backlog_storage_dirty = False
    else:
        st.session_state.backlog_storage_hydrated = True
        return None

    if decoded.dropped:
        st.session_state.backlog_storage_dropped = decoded.dropped
    return decoded


def persist_backlog_storage(graph_data: GraphData) -> None:
    if not st.session_state.get("backlog_storage_dirty", False):
        return None

    backlog_state: BacklogState = st.session_state.backlog_state
    if st.session_state.get("backlog_storage_last_order") == backlog_state.order:
        st.session_state.backlog_storage_dirty = False
        return None

    payload = encode_backlog(graph_data, backlog_state)
    serialized = json.dumps(payload, sort_keys=True)
    if st.session_state.get("backlog_storage_last") == serialized:
        st.session_state.backlog_storage_dirty = False
        return None

    st.session_state.backlog_storage_last = serialized
    st.session_state.backlog_storage_last_order = backlog_state.order
    st.session_state.backlog_storage_dirty = False
    _write_backlog_storage(payload)
    st.session_state.backlog_storage_write_error = None
    return None
