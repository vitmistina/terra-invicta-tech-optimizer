from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

logger = logging.getLogger(__name__)


class NodeType(str, Enum):
    TECH = "tech"
    PROJECT = "project"


@dataclass
class Node:
    identifier: str
    friendly_name: str
    node_type: NodeType
    category: str | None
    prereqs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LoadReport:
    nodes: dict[str, Node]
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)


class InputLoader:
    """Load technology and project definitions from structured files."""

    SUPPORTED_EXTENSIONS = {".json", ".csv", ".tsv"}

    def __init__(self, input_dir: Path):
        self.input_dir = Path(input_dir)

    def load(self) -> LoadReport:
        nodes: dict[str, Node] = {}
        warnings: list[str] = []
        errors: list[str] = []

        for path in sorted(self.input_dir.glob("*")):
            if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
                message = f"Ignoring unsupported file: {path.name}"
                warnings.append(message)
                logger.warning(message)
                continue

            try:
                records = list(self._parse_file(path))
            except (json.JSONDecodeError, UnicodeDecodeError, csv.Error) as exc:  # pragma: no cover - defensive
                message = f"Failed to parse {path.name}: {exc}"
                errors.append(message)
                logger.error(message)
                continue

            for record in records:
                try:
                    node = self._build_node(record, source=path)
                except ValueError as exc:
                    message = str(exc)
                    errors.append(message)
                    logger.error(message)
                    continue

                if node.identifier in nodes:
                    message = f"Duplicate node id {node.identifier} in {path.name}; keeping first occurrence"
                    warnings.append(message)
                    logger.warning(message)
                    continue
                nodes[node.identifier] = node

        return LoadReport(nodes=nodes, warnings=warnings, errors=errors)

    def _parse_file(self, path: Path) -> Iterable[dict[str, Any]]:
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text())
            if isinstance(data, dict):
                yield data
            else:
                yield from data
            return

        delimiter = "," if path.suffix.lower() == ".csv" else "\t"
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, delimiter=delimiter)
            for row in reader:
                yield {k: v for k, v in row.items() if k is not None}

    def _build_node(self, record: dict[str, Any], source: Path) -> Node:
        identifier = record.get("dataName") or record.get("id") or record.get("name")
        if not identifier:
            raise ValueError(f"Record in {source.name} is missing an identifier")

        friendly_name = record.get("friendlyName") or record.get("label") or identifier
        category = record.get("techCategory") or record.get("category")
        prereqs_raw = record.get("prereqs") or record.get("dependencies") or []
        prereqs = self._normalize_prereqs(prereqs_raw)

        node_type = self._infer_node_type(record, source)
        metadata = {
            k: v
            for k, v in record.items()
            if k not in {"dataName", "friendlyName", "techCategory", "prereqs", "dependencies", "type", "node_type", "nodeType"}
        }

        return Node(
            identifier=str(identifier),
            friendly_name=str(friendly_name),
            node_type=node_type,
            category=category,
            prereqs=prereqs,
            metadata=metadata,
        )

    def _normalize_prereqs(self, prereqs_raw: Any) -> list[str]:
        if prereqs_raw is None:
            return []
        if isinstance(prereqs_raw, str):
            return [item.strip() for item in prereqs_raw.split(",") if item.strip()]
        if isinstance(prereqs_raw, Iterable):
            return [str(item) for item in prereqs_raw if str(item).strip()]
        return []

    def _infer_node_type(self, record: dict[str, Any], source: Path) -> NodeType:
        explicit_type = record.get("type") or record.get("node_type") or record.get("nodeType")
        if isinstance(explicit_type, str):
            normalized = explicit_type.strip().lower()
            if normalized.startswith("proj"):
                return NodeType.PROJECT
            if normalized.startswith("tech"):
                return NodeType.TECH

        stem = source.stem.lower()
        if "project" in stem or "_projects" in stem:
            return NodeType.PROJECT

        if record.get("AI_projectRole") is not None:
            return NodeType.PROJECT

        return NodeType.TECH
