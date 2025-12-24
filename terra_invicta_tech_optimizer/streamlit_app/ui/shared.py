from __future__ import annotations

import json
import re
from html import escape as html_escape
from pathlib import Path

import streamlit as st

from terra_invicta_tech_optimizer import BacklogState, FlatNodeList, GraphFilters

from ..config import CATEGORY_ICON_MAP, STATIC_DIR


def format_cost(cost: int | None) -> str:
    return f"{cost:,}" if cost is not None else "N/A"


def category_icon_path(category: str | None) -> Path | None:
    if not category:
        return None
    key = re.sub(r"[^a-z0-9]", "", str(category).casefold())
    filename = CATEGORY_ICON_MAP.get(key)
    if not filename:
        return None
    path = STATIC_DIR / filename
    return path if path.exists() else None


def label_for_index(index: int, *, flat_list: FlatNodeList) -> str:
    row = flat_list.rows[index]
    kind = row.node_type.value.title()
    category = row.category or "Uncategorized"
    return f"{row.friendly_name} | {kind} | {category} [{row.node_id}]"


def option_choices(nodes) -> dict[str, str]:
    entries: dict[str, str] = {}
    for node_id, node in nodes.items():
        label_parts = [node.friendly_name]
        label_parts.append(node.node_type.value.title())
        if node.category:
            label_parts.append(node.category)
        label = " | ".join(label_parts) + f" [{node_id}]"
        entries[label] = node_id
    return dict(sorted(entries.items(), key=lambda item: item[0].lower()))


def parse_backlog_order(value: str, backlog: BacklogState) -> tuple[int, ...] | None:
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


def render_validation(result) -> None:
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


def friendly_name(node_id: str, nodes) -> str:
    node = nodes.get(node_id)
    return node.friendly_name if node else node_id


def matches_filters(
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


def render_sortable_backlog_compact(
    backlog: BacklogState, *, flat_list: FlatNodeList
) -> None:
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
    st.components.v1.html(html, height=height, scrolling=True)


def render_sortable_backlog_panel(
    backlog: BacklogState, *, flat_list: FlatNodeList
) -> None:
    """Custom HTML/JS drag-drop backlog with theme-safe styling."""
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
        if (!input) return;
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
        if (!target || target === dragItem) return;
        const rect = target.getBoundingClientRect();
        const next = (event.clientY - rect.top) > (rect.height / 2);
        list.insertBefore(dragItem, next ? target.nextSibling : target);
      }});

      list.addEventListener("drop", () => updateInput());
      list.addEventListener("dragend", () => updateInput());
    }}
    </script>
    <style>
    .backlog-root {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }}
    .backlog-list {{
      list-style: none;
      padding-left: 0;
      margin: 0;
    }}
    .backlog-item {{
      padding: 10px 12px;
      margin-bottom: 8px;
      background: white;
      border: 1px solid #d1d5db;
      border-radius: 8px;
      cursor: grab;
      user-select: none;
      color: #1f2937;
      font-size: 0.9rem;
      transition: box-shadow 0.15s, border-color 0.15s;
    }}
    .backlog-item:hover {{
      border-color: #9ca3af;
      box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }}
    .backlog-item:active {{
      cursor: grabbing;
      box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }}
    @media (prefers-color-scheme: dark) {{
      .backlog-item {{
        background: #374151;
        border-color: #4b5563;
        color: #f3f4f6;
      }}
      .backlog-item:hover {{
        border-color: #6b7280;
      }}
    }}
    </style>
    """
    height = min(250, 46 * max(1, len(items)) + 10)
    st.components.v1.html(html, height=height, scrolling=True)
