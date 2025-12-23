from __future__ import annotations

import json
import re
from dataclasses import asdict
from html import escape as html_escape
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from terra_invicta_tech_optimizer import (
    GraphExplorer,
    GraphFilters,
    GraphValidator,
    BacklogState,
    DecodedBacklog,
    FlatNodeList,
    GraphData,
    InputLoader,
    ListFilters,
    SimulationConfig,
    SimulationSlotConfig,
    backlog_add,
    backlog_remove,
    backlog_reorder,
    build_flat_list_view,
    build_flat_node_list,
    build_graph_data,
    decode_backlog,
    encode_backlog,
)
from terra_invicta_tech_optimizer.backlog_storage import STORAGE_KEY


BASE_DIR = Path(__file__).parent
INPUT_DIR = BASE_DIR / "inputs"
STATIC_DIR = BASE_DIR / "static"

CATEGORY_ICON_MAP = {
    "energy": "30px-Tech_energy_icon.png",
    "informationscience": "30px-Tech_info_icon.png",
    "lifescience": "30px-Tech_life_icon.png",
    "materials": "30px-Tech_material_icon.png",
    "militaryscience": "30px-Tech_military_icon.png",
    "socialscience": "30px-Tech_social_icon.png",
    "spacescience": "30px-Tech_space_icon.png",
    "xenology": "30px-Tech_xeno_icon.png",
    "info": "30px-Tech_info_icon.png",
    "life": "30px-Tech_life_icon.png",
    "military": "30px-Tech_military_icon.png",
    "social": "30px-Tech_social_icon.png",
    "space": "30px-Tech_space_icon.png",
    "xeno": "30px-Tech_xeno_icon.png",
}


def _load_inputs(reload_token: int):
    loader = InputLoader(INPUT_DIR)
    return loader.load()


@st.cache_data(show_spinner=False)
def load_inputs(reload_token: int):
    return _load_inputs(reload_token)


def validate_graph(nodes):
    return GraphValidator(nodes).validate()


def _ensure_base_state() -> None:
    if "reload_token" not in st.session_state:
        st.session_state.reload_token = 0

    if "filters" not in st.session_state:
        st.session_state.filters = ListFilters.reset()

    if "selected" not in st.session_state:
        st.session_state.selected = None

    if "backlog_storage_dirty" not in st.session_state:
        st.session_state.backlog_storage_dirty = False


def get_models(nodes) -> tuple[GraphData, FlatNodeList]:
    reload_token = st.session_state.get("reload_token", 0)
    models_state = st.session_state.get("models")

    if models_state and models_state.get("token") == reload_token:
        return models_state["graph_data"], models_state["flat_list"]

    graph_data = build_graph_data(nodes)
    flat_list = build_flat_node_list(graph_data, nodes)
    st.session_state.models = {
        "token": reload_token,
        "graph_data": graph_data,
        "flat_list": flat_list,
    }
    return graph_data, flat_list


def _coerce_indices(value, *, graph_data: GraphData) -> list[int]:
    if value is None:
        return []
    if isinstance(value, (set, frozenset, tuple, list)):
        items = list(value)
    else:
        items = [value]

    indices: list[int] = []
    for item in items:
        if isinstance(item, int):
            if 0 <= item < graph_data.size:
                indices.append(item)
            continue
        node_id = str(item)
        idx = graph_data.id_to_index.get(node_id)
        if idx is not None:
            indices.append(idx)
    return indices


def ensure_state(nodes, *, graph_data: GraphData) -> None:
    _ensure_base_state()

    if st.session_state.selected not in nodes:
        st.session_state.selected = None

    if "backlog_state" not in st.session_state:
        legacy = st.session_state.get("backlog")
        legacy_indices = _coerce_indices(legacy, graph_data=graph_data)
        order = tuple(dict.fromkeys(legacy_indices))
        st.session_state.backlog_state = BacklogState(
            order=order, members=frozenset(order)
        )
    else:
        backlog_state: BacklogState = st.session_state.backlog_state
        order = tuple(idx for idx in backlog_state.order if 0 <= idx < graph_data.size)
        st.session_state.backlog_state = BacklogState(
            order=order, members=frozenset(order)
        )

    if "completed" not in st.session_state:
        legacy = st.session_state.get("completed")
        st.session_state.completed = set(_coerce_indices(legacy, graph_data=graph_data))
    else:
        st.session_state.completed = {
            idx for idx in st.session_state.completed if 0 <= idx < graph_data.size
        }


def _storage_component(script: str) -> Any:
    return components.html(
        f"""
        <script>
        {script}
        </script>
        """,
        height=0,
        width=0,
        scrolling=False,
        key="_backlog_storage_component",
    )


def _read_backlog_storage() -> dict | None:
    st.session_state.setdefault("backlog_storage_attempts", 0)

    # Avoid spawning additional background iframes once we've tried a few times.
    if st.session_state.backlog_storage_attempts > 3:
        return None

    st.session_state.backlog_storage_attempts += 1
    return _storage_component(
        f"""
        (() => {{
            const sendValue = (value) => window.parent.postMessage({{type: "streamlit:setComponentValue", value}}, "*");
            try {{
                const raw = window.localStorage.getItem("{STORAGE_KEY}");
                if (!raw) {{
                    sendValue(null);
                    return;
                }}
                try {{
                    const parsed = JSON.parse(raw);
                    sendValue({{ payload: parsed }});
                }} catch (err) {{
                    sendValue({{ payload: null, error: String(err) }});
                }}
            }} catch (err) {{
                sendValue({{ payload: null, error: String(err) }});
            }}
        }})();
        """,
    )


def _write_backlog_storage(payload: dict) -> dict | None:
    encoded = json.dumps(payload, sort_keys=True)
    return _storage_component(
        f"""
        (() => {{
            const sendValue = (value) => window.parent.postMessage({{type: "streamlit:setComponentValue", value}}, "*");
            try {{
                const payload = {encoded};
                const serialized = JSON.stringify(payload);
                window.localStorage.setItem("{STORAGE_KEY}", serialized);
                sendValue({{ ok: true }});
            }} catch (err) {{
                sendValue({{ ok: false, error: String(err) }});
            }}
        }})();
        """,
    )


def hydrate_backlog_from_storage(graph_data: GraphData) -> DecodedBacklog | None:
    if st.session_state.get("backlog_storage_hydrated"):
        return None

    response = _read_backlog_storage()
    if not response:
        return None

    payload = response.get("payload") if isinstance(response, dict) else None
    if payload is None:
        st.session_state.backlog_storage_hydrated = True
        return None

    decoded = decode_backlog(payload, graph_data)
    if decoded:
        st.session_state.backlog_state = decoded.backlog
        st.session_state.backlog_storage_hydrated = True
        st.session_state.backlog_storage_last = json.dumps(payload, sort_keys=True)
        st.session_state.backlog_storage_dirty = False
    else:
        st.session_state.backlog_storage_hydrated = True
        return None

    if decoded.dropped:
        st.session_state.backlog_storage_dropped = decoded.dropped
    return decoded


def persist_backlog_storage(graph_data: GraphData) -> dict | None:
    if not st.session_state.get("backlog_storage_dirty", False):
        return None

    backlog_state: BacklogState = st.session_state.backlog_state
    payload = encode_backlog(graph_data, backlog_state)
    serialized = json.dumps(payload, sort_keys=True)
    if st.session_state.get("backlog_storage_last") == serialized:
        st.session_state.backlog_storage_dirty = False
        return None

    st.session_state.backlog_storage_last = serialized
    st.session_state.backlog_storage_dirty = False
    result = _write_backlog_storage(payload)
    if isinstance(result, dict) and not result.get("ok", True):
        st.session_state.backlog_storage_write_error = result.get("error")
    return result


def _persist_after_mutation() -> None:
    models = st.session_state.get("models")
    if not models:
        return
    graph_data: GraphData | None = models.get("graph_data")
    if graph_data is None:
        return

    st.session_state.backlog_storage_dirty = True
    persist_backlog_storage(graph_data)


def get_explorer(nodes):
    reload_token = st.session_state.get("reload_token", 0)
    explorer_state = st.session_state.get("explorer")

    if explorer_state and explorer_state.get("token") == reload_token:
        return explorer_state["instance"]

    explorer = GraphExplorer(nodes)
    st.session_state.explorer = {"instance": explorer, "token": reload_token}
    return explorer


def reset_filters():
    st.session_state.filters = ListFilters.reset()


def apply_backlog_addition(node_index: int | None):
    if node_index is None:
        return
    st.session_state.backlog_state = backlog_add(
        st.session_state.backlog_state, node_index
    )
    _persist_after_mutation()


def remove_backlog_item(node_index: int | None):
    if node_index is None:
        return
    st.session_state.backlog_state = backlog_remove(
        st.session_state.backlog_state, node_index
    )
    _persist_after_mutation()


def build_graphviz(view):
    lines = ["digraph G {"]
    lines.append("rankdir=LR;")
    lines.append("graph [pad=0.2];")
    lines.append("node [style=filled];")

    for node in view.nodes:
        if node.is_hidden:
            continue

        base_color = node.style.color
        fillcolor = _dim_color(base_color, 0.25) if node.is_dimmed else base_color
        stroke = "#ff6b6b" if node.is_selected else "#4b5563"
        penwidth = "3" if node.is_selected or node.in_backlog else "1.5"
        peripheries = "2" if node.in_backlog else "1"
        tooltip = _build_tooltip(node)

        badge = []
        if node.is_completed:
            badge.append("✓ Completed")
        if node.is_prerequisite:
            badge.append("Prereq")
        if node.is_dependent:
            badge.append("Dependent")
        if node.in_backlog:
            badge.append("Backlog")
        badge_text = " | ".join(badge)

        label_lines = [f"<B>{node.label}</B>"]
        if node.category:
            label_lines.append(node.category)
        if badge_text:
            label_lines.append(f"<FONT POINT-SIZE='10'>{badge_text}</FONT>")

        label = "<" + "<BR/>".join(label_lines) + ">"
        shape = "box" if node.node_type.value == "project" else "ellipse"

        lines.append(
            f'"{node.identifier}" [label={label} shape={shape} fillcolor="{fillcolor}" color="{stroke}" penwidth={penwidth} peripheries={peripheries} tooltip="{tooltip}" fontname="Inter" fontsize=12];'
        )

    for edge in view.edges:
        if edge.is_hidden:
            continue
        color = "#94a3b8"
        if edge.is_highlighted:
            color = "#fb7185"
        elif edge.is_dimmed:
            color = "#cbd5e1"
        lines.append(
            f'"{edge.source}" -> "{edge.target}" [color="{color}" penwidth=1.4 arrowsize=0.8];'
        )

    lines.append("}")
    return "\n".join(lines)


def _dim_color(hex_color: str, factor: float) -> str:
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    return f"#{r:02x}{g:02x}{b:02x}"


def _build_tooltip(node):
    details = [node.label]
    if node.category:
        details.append(f"Category: {node.category}")
    if node.prereqs:
        details.append("Prereqs: " + ", ".join(node.prereqs))
    for key, value in node.metadata.items():
        details.append(f"{key}: {value}")
    return " | ".join(details)


def _friendly_name(node_id: str, nodes) -> str:
    node = nodes.get(node_id)
    return node.friendly_name if node else node_id


def _label_for_index(index: int, *, flat_list: FlatNodeList) -> str:
    row = flat_list.rows[index]
    kind = row.node_type.value.title()
    category = row.category or "Uncategorized"
    return f"{row.friendly_name} | {kind} | {category} [{row.node_id}]"


def _option_choices(nodes):
    entries: dict[str, str] = {}
    for node_id, node in nodes.items():
        label_parts = [node.friendly_name]
        label_parts.append(node.node_type.value.title())
        if node.category:
            label_parts.append(node.category)
        label = " | ".join(label_parts) + f" [{node_id}]"
        entries[label] = node_id
    return dict(sorted(entries.items(), key=lambda item: item[0].lower()))


def _node_cost(node) -> int | None:
    raw_cost = node.metadata.get("researchCost")
    if raw_cost is None:
        return None
    try:
        cost = int(raw_cost)
    except (TypeError, ValueError):
        return None
    if cost < 0:
        return None
    return cost


def _format_cost(cost: int | None) -> str:
    return f"{cost:,}" if cost is not None else "N/A"


def _category_icon_path(category: str | None) -> Path | None:
    if not category:
        return None
    key = re.sub(r"[^a-z0-9]", "", str(category).casefold())
    filename = CATEGORY_ICON_MAP.get(key)
    if not filename:
        return None
    path = STATIC_DIR / filename
    return path if path.exists() else None


def _matches_filters(
    node, completed: set[str], backlog: set[str], filters: GraphFilters
) -> bool:
    is_completed = node.identifier in completed
    in_backlog = node.identifier in backlog
    passes_category = not filters.categories or (node.category in filters.categories)
    passes_completion = (is_completed and filters.include_completed) or (
        not is_completed and filters.include_incomplete
    )
    passes_backlog = (not filters.backlog_only) or in_backlog
    return passes_category and passes_completion and passes_backlog


def _sort_nodes_for_list(nodes, mode: str):
    if mode.startswith("Tech cost"):

        def _cost_key(node):
            cost = _node_cost(node)
            missing = cost is None
            return (missing, -(cost or 0), node.friendly_name.lower())

        return sorted(nodes, key=_cost_key)
    return sorted(nodes, key=lambda node: node.friendly_name.lower())


def _parse_backlog_order(value: str, backlog: BacklogState) -> tuple[int, ...] | None:
    if not value:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, list):
        return None

    allowed = backlog.members
    seen: set[int] = set()
    cleaned: list[int] = []

    for item in parsed:
        try:
            idx = int(item)
        except (TypeError, ValueError):
            continue
        if idx in allowed and idx not in seen:
            cleaned.append(idx)
            seen.add(idx)

    for idx in backlog.order:
        if idx not in seen:
            cleaned.append(idx)
            seen.add(idx)

    return tuple(cleaned)


def _render_sortable_backlog(backlog: BacklogState, *, flat_list: FlatNodeList) -> None:
    # Custom HTML/JS updates a hidden Streamlit text input with the reordered IDs.
    items = []
    for idx in backlog.order:
        if idx < 0 or idx >= len(flat_list.rows):
            continue
        row = flat_list.rows[idx]
        label = f"{row.friendly_name} ({row.node_type.value.title()})"
        safe_label = html_escape(label)
        safe_id = html_escape(str(idx))
        items.append(
            f'<li class="backlog-item" draggable="true" data-id="{safe_id}">{safe_label}</li>'
        )

    list_html = "\n".join(items)
    html = f"""
    <div class="backlog-root">
      <ul class="backlog-list">
        {list_html}
      </ul>
    </div>
    <script>
    const list = document.querySelector(".backlog-list");
    if (list) {{
      const parentDoc = window.parent.document;
      let dragItem = null;

      const updateInput = () => {{
        const order = Array.from(list.querySelectorAll(".backlog-item")).map((el) => el.dataset.id);
        const input = parentDoc.querySelector("input[aria-label='Backlog order']");
        if (!input) {{
          return;
        }}
        input.value = JSON.stringify(order);
        input.dispatchEvent(new Event("input", {{ bubbles: true }}));
      }};

      list.addEventListener("dragstart", (event) => {{
        dragItem = event.target.closest(".backlog-item");
        event.dataTransfer.effectAllowed = "move";
      }});

      list.addEventListener("dragover", (event) => {{
        event.preventDefault();
        const target = event.target.closest(".backlog-item");
        if (!target || target === dragItem) {{
          return;
        }}
        const rect = target.getBoundingClientRect();
        const next = (event.clientY - rect.top) > (rect.height / 2);
        list.insertBefore(dragItem, next ? target.nextSibling : target);
      }});

      list.addEventListener("drop", () => {{
        updateInput();
      }});

      list.addEventListener("dragend", () => {{
        updateInput();
      }});
    }}
    </script>
    <style>
    .backlog-root {{
      font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
    }}
    .backlog-list {{
      list-style: none;
      padding-left: 0;
      margin: 0;
    }}
    .backlog-item {{
      padding: 8px 10px;
      margin-bottom: 6px;
      background: #f8fafc;
      border: 1px solid #cbd5f5;
      border-radius: 6px;
      cursor: grab;
      user-select: none;
    }}
    .backlog-item:active {{
      cursor: grabbing;
    }}
    </style>
    """
    height = min(360, 38 * max(1, len(items)) + 20)
    components.html(html, height=height, scrolling=True)


def render_validation(result):
    if result.has_errors:
        with st.container(border=True):
            st.error("Validation failed. Resolve blocking issues to continue planning.")
            for issue in result.errors:
                st.write(f"**{issue.message}**: {', '.join(issue.nodes)}")
    else:
        with st.container(border=True):
            st.success("Graph validated. Ready for planning.")
            if result.warnings:
                st.warning("Warnings detected:")
                for warning in result.warnings:
                    st.write(f"**{warning.message}**: {', '.join(warning.nodes)}")


def render_filters(nodes):
    _, flat_list = get_models(nodes)
    filters: ListFilters = st.session_state.filters
    categories = list(flat_list.categories)

    st.subheader("Filters")
    st.caption(
        "Focus the list and results on categories, completion state, or backlog."
    )

    selected_categories = st.multiselect(
        "Categories",
        options=categories,
        default=sorted(filters.categories) if filters.categories else [],
    )

    include_completed = st.checkbox("Show completed", value=filters.include_completed)
    include_incomplete = st.checkbox(
        "Show incomplete", value=filters.include_incomplete
    )
    backlog_only = st.checkbox("Backlog only", value=filters.backlog_only)

    st.session_state.filters = ListFilters(
        categories=frozenset(selected_categories) if selected_categories else None,
        include_completed=include_completed,
        include_incomplete=include_incomplete,
        backlog_only=backlog_only,
    )

    cols = st.columns(2)
    with cols[0]:
        st.button(
            "Reset filters", type="secondary", on_click=reset_filters, width="stretch"
        )
    with cols[1]:
        filters = st.session_state.filters
        if (
            filters.categories
            or not filters.include_completed
            or not filters.include_incomplete
            or backlog_only
        ):
            st.info("Filters are active")
        else:
            st.caption("All nodes visible")


def render_node_list(nodes):
    st.subheader("Technology and project list")
    st.caption("Click an item to add it to the backlog.")
    st.markdown(
        """
        <style>
        .tech-list-scope {
          --tech-text: #e2e8f0;
          --tech-muted: #94a3b8;
          --tech-border: #334155;
          --tech-pill: #1f2937;
          --tech-tech-bg: #1e3a8a;
          --tech-tech-border: #1d4ed8;
          --tech-tech-text: #dbeafe;
          --tech-proj-bg: #14532d;
          --tech-proj-border: #16a34a;
          --tech-proj-text: #dcfce7;
        }
        .tech-badge {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 28px;
          height: 28px;
          border-radius: 8px;
          font-weight: 700;
          font-size: 0.85rem;
          letter-spacing: 0.02em;
          color: var(--tech-text);
          background: var(--tech-pill);
          border: 1px solid var(--tech-border);
        }
        .tech-badge.tech {
          background: var(--tech-tech-bg);
          border-color: var(--tech-tech-border);
          color: var(--tech-tech-text);
        }
        .tech-badge.project {
          background: var(--tech-proj-bg);
          border-color: var(--tech-proj-border);
          color: var(--tech-proj-text);
        }
        .tech-name { font-weight: 600; color: var(--tech-text); }
        .tech-status { font-size: 0.8rem; color: var(--tech-muted); margin-top: 2px; }
        .tech-cost {
          text-align: right;
          font-family: "Consolas", "Courier New", monospace;
          font-variant-numeric: tabular-nums;
          color: var(--tech-text);
          font-size: 0.6rem;
        }
        .tech-dim { opacity: 0.45; }
        .tech-header {
          text-transform: uppercase;
          font-size: 0.72rem;
          letter-spacing: 0.08em;
          color: var(--tech-muted);
          margin-bottom: 6px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    sort_mode = st.radio(
        "Order within category",
        ("Tech cost (desc)", "Friendly name (A-Z)"),
        horizontal=True,
    )

    _, flat_list = get_models(nodes)
    filters: ListFilters = st.session_state.filters
    completed: set[int] = set(st.session_state.completed)
    backlog_state: BacklogState = st.session_state.backlog_state

    view = build_flat_list_view(
        flat_list,
        filters=filters,
        completed=completed,
        backlog_members=set(backlog_state.members),
        sort_mode=sort_mode,
    )

    if not view.visible_by_category:
        st.caption("No items match the current filters.")
        return

    for category in flat_list.categories:
        visible_indices = view.visible_by_category.get(category)
        if not visible_indices:
            continue
        st.markdown(f"**{category}**")
        header_cols = st.columns([0.1, 0.6, 0.14, 0.08])
        header_cols[0].markdown(
            "<div class='tech-header'>Category</div>", unsafe_allow_html=True
        )
        header_cols[1].markdown(
            "<div class='tech-header'>Name</div>", unsafe_allow_html=True
        )
        header_cols[2].markdown(
            "<div class='tech-header' style='text-align:right;'>Cost</div>",
            unsafe_allow_html=True,
        )
        header_cols[3].markdown(
            "<div class='tech-header' style='text-align:center;'>Add</div>",
            unsafe_allow_html=True,
        )

        for idx in visible_indices:
            row = flat_list.rows[idx]
            cost_text = _format_cost(row.cost)
            status = []
            if idx in backlog_state.members:
                status.append("Backlog")
            if idx in completed:
                status.append("Completed")
            status_text = ", ".join(status) if status else ""

            disabled = idx in backlog_state.members
            dim_class = ""
            badge_text = "T" if row.node_type.value == "tech" else "P"
            badge_kind = "tech" if row.node_type.value == "tech" else "project"

            row_cols = st.columns([0.1, 0.6, 0.14, 0.08])
            icon_path = _category_icon_path(row.category)
            if icon_path:
                row_cols[0].image(str(icon_path), width=24)
            else:
                row_cols[0].markdown(
                    f"<div class='tech-list-scope tech-name{dim_class}'>{html_escape(row.category or 'Uncategorized')}</div>",
                    unsafe_allow_html=True,
                )
            name_html = f"<div class='tech-name{dim_class}'>{html_escape(row.friendly_name)}</div>"
            if status_text:
                name_html += f"<div class='tech-status{dim_class}'>{html_escape(status_text)}</div>"
            row_cols[1].markdown(
                f"<div class='tech-list-scope'>{name_html}</div>",
                unsafe_allow_html=True,
            )
            row_cols[2].markdown(
                f"<div class='tech-list-scope tech-cost{dim_class}'>{cost_text}</div>",
                unsafe_allow_html=True,
            )
            row_cols[3].button(
                "✅" if idx in backlog_state.members else "➕",
                key=f"list-{row.node_id}",
                on_click=apply_backlog_addition,
                args=(idx,),
                width="stretch",
                disabled=disabled,
            )


def render_backlog(nodes):
    st.subheader("Backlog")
    st.caption("Drag and drop to reorder. Use the list to add items.")

    graph_data, flat_list = get_models(nodes)
    backlog: BacklogState = st.session_state.backlog_state

    if not backlog.order:
        st.caption("No backlog items yet.")
        return

    order_value = st.text_input(
        "Backlog order",
        value=json.dumps([str(idx) for idx in backlog.order]),
        key="backlog_order",
        label_visibility="collapsed",
    )
    st.markdown(
        "<style>input[aria-label='Backlog order'] { display: none; }</style>",
        unsafe_allow_html=True,
    )
    new_order = _parse_backlog_order(order_value, backlog)
    if new_order is not None and new_order != backlog.order:
        st.session_state.backlog_state = backlog_reorder(backlog, new_order)
        backlog = st.session_state.backlog_state
        st.session_state.backlog_order = json.dumps([str(idx) for idx in backlog.order])
        _persist_after_mutation()

    _render_sortable_backlog(backlog, flat_list=flat_list)

    remove_map: dict[str, int] = {}
    for idx in backlog.order:
        remove_map[_label_for_index(idx, flat_list=flat_list)] = idx

    selected_label = st.selectbox(
        "Remove item", ["Select item"] + list(remove_map.keys())
    )
    node_to_remove = remove_map.get(selected_label)
    st.button(
        "Remove selected",
        on_click=remove_backlog_item,
        args=(node_to_remove,),
        width="stretch",
        type="secondary",
        disabled=node_to_remove is None,
    )


def render_completion(nodes):
    st.subheader("Completion state")
    st.caption("Mark items you've already finished to de-emphasize them.")
    _, flat_list = get_models(nodes)
    options = {
        _label_for_index(idx, flat_list=flat_list): idx
        for idx in range(len(flat_list.rows))
    }
    default_labels = [
        label for label, idx in options.items() if idx in st.session_state.completed
    ]
    selected = st.multiselect(
        "Completed items", options=list(options.keys()), default=default_labels
    )
    st.session_state.completed = {options[name] for name in selected}


def render_graph(explorer, nodes):
    st.subheader("Graph explorer")
    st.caption(
        "Hover for details, select a node to focus prerequisites and dependents."
    )

    options = _option_choices(nodes)
    option_labels = ["None"] + list(options.keys())
    default_label = next(
        (
            label
            for label, node_id in options.items()
            if node_id == st.session_state.selected
        ),
        "None",
    )
    selected_label = st.selectbox(
        "Focus node", option_labels, index=option_labels.index(default_label)
    )
    st.session_state.selected = options.get(selected_label)

    graph_data, flat_list = get_models(nodes)
    list_filters: ListFilters = st.session_state.filters
    graph_filters = GraphFilters(
        categories=set(list_filters.categories) if list_filters.categories else None,
        include_completed=list_filters.include_completed,
        include_incomplete=list_filters.include_incomplete,
        backlog_only=list_filters.backlog_only,
        hide_filtered=True,
    )

    graph_view = explorer.build_view(
        selected=st.session_state.selected,
        completed={graph_data.node_ids[idx] for idx in st.session_state.completed},
        backlog=[
            graph_data.node_ids[idx] for idx in st.session_state.backlog_state.order
        ],
        filters=graph_filters,
    )

    graphviz_spec = build_graphviz(graph_view)
    st.graphviz_chart(graphviz_spec, width="stretch")

    with st.expander("Selection details", expanded=bool(st.session_state.selected)):
        if st.session_state.selected:
            node = nodes.get(st.session_state.selected)
            st.markdown(f"**{node.friendly_name}** ({node.node_type.value.title()})")
            st.write(f"Category: {node.category or 'Uncategorized'}")
            if node.prereqs:
                prereq_labels = ", ".join(
                    _friendly_name(pid, nodes) for pid in node.prereqs
                )
                st.write(f"Prerequisites: {prereq_labels}")
            if node.metadata:
                st.json(node.metadata)

            graph_data, _ = get_models(nodes)
            node_index = graph_data.id_to_index.get(node.identifier)
            st.button(
                "Quick-add to backlog",
                on_click=apply_backlog_addition,
                args=(node_index,),
                type="primary",
            )
        else:
            st.caption("Select a node to see its dependencies and metadata.")

    with st.expander("Graph debug data"):
        st.write("Filters", asdict(st.session_state.filters))
        st.write("Selected", st.session_state.selected)
        st.write("Completed", list(st.session_state.completed))
        st.write("Backlog", list(st.session_state.backlog_state.order))


def main():
    # Redirect to Start here page as the default landing
    st.switch_page("pages/Start_here.py")


if __name__ == "__main__":
    main()
