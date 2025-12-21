from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set

from .input_loader import Node, NodeType


@dataclass
class ValidationIssue:
    message: str
    nodes: list[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    def summary(self) -> str:
        error_count = len(self.errors)
        warning_count = len(self.warnings)
        return f"{error_count} error(s), {warning_count} warning(s)"


class GraphValidator:
    def __init__(self, nodes: Dict[str, Node]):
        self.nodes = nodes

    def validate(self) -> ValidationResult:
        result = ValidationResult()
        self._check_missing_references(result)
        self._check_cycles(result)
        return result

    def _check_missing_references(self, result: ValidationResult) -> None:
        defined_names = set(self.nodes.keys())
        missing_map: Dict[str, List[str]] = {}

        for node in self.nodes.values():
            for prereq in node.prereqs:
                if prereq not in defined_names:
                    missing_map.setdefault(prereq, []).append(node.identifier)

        for missing, dependents in missing_map.items():
            result.errors.append(
                ValidationIssue(
                    message=f"Missing reference: {missing}",
                    nodes=dependents,
                )
            )

    def _check_cycles(self, result: ValidationResult) -> None:
        visited: Set[str] = set()
        stack: Set[str] = set()

        def dfs(node_id: str) -> None:
            if node_id in stack:
                result.errors.append(
                    ValidationIssue(
                        message=f"Cycle detected involving {node_id}",
                        nodes=[node_id],
                    )
                )
                return
            if node_id in visited:
                return

            visited.add(node_id)
            stack.add(node_id)

            node = self.nodes.get(node_id)
            if node:
                for prereq in node.prereqs:
                    if prereq in self.nodes:
                        dfs(prereq)

            stack.remove(node_id)

        for node_id in self.nodes:
            if node_id not in visited:
                dfs(node_id)