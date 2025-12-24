from __future__ import annotations


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


def _build_tooltip(node) -> str:
    details = [node.label]
    if node.category:
        details.append(f"Category: {node.category}")
    if node.prereqs:
        details.append("Prereqs: " + ", ".join(node.prereqs))
    for key, value in node.metadata.items():
        details.append(f"{key}: {value}")
    return " | ".join(details)
