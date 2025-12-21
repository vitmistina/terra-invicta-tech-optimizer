from pathlib import Path

import pytest

from terra_invicta_tech_optimizer import GraphValidator, InputLoader, NodeType


def test_loads_json_and_filters_supported(tmp_path: Path):
    tech_file = tmp_path / "techs.json"
    tech_file.write_text(
        """
        [
          {"dataName": "TechA", "friendlyName": "Tech A", "techCategory": "Energy", "prereqs": []},
          {"dataName": "ProjectAlpha", "friendlyName": "Alpha", "prereqs": ["TechA"], "AI_projectRole": "Story"}
        ]
        """
    )

    csv_file = tmp_path / "projects.csv"
    csv_file.write_text("dataName,friendlyName,prereqs,type\nProjB,Project B,TechA,project\n")

    unsupported = tmp_path / "ignore.me"
    unsupported.write_text("noop")

    loader = InputLoader(tmp_path)
    report = loader.load()

    assert set(report.nodes.keys()) == {"TechA", "ProjectAlpha", "ProjB"}
    assert report.nodes["TechA"].node_type is NodeType.TECH
    assert report.nodes["ProjectAlpha"].node_type is NodeType.PROJECT
    assert report.nodes["ProjB"].node_type is NodeType.PROJECT
    assert any("unsupported" in warning for warning in report.warnings)


def test_validate_missing_and_cycles(tmp_path: Path):
    techs = tmp_path / "techs.json"
    techs.write_text(
        """
        [
          {"dataName": "TechA", "friendlyName": "Tech A", "prereqs": ["TechB"]},
          {"dataName": "TechB", "friendlyName": "Tech B", "prereqs": ["TechA", "Missing"]}
        ]
        """
    )

    loader = InputLoader(tmp_path)
    report = loader.load()
    validator = GraphValidator(report.nodes)
    result = validator.validate()

    assert result.has_errors
    messages = {issue.message for issue in result.errors}
    assert any("Missing reference" in message for message in messages)
    assert any("Cycle detected" in message for message in messages)


def test_project_requires_tech_dependency(tmp_path: Path):
    input_file = tmp_path / "projects.tsv"
    input_file.write_text("dataName\tprereqs\ttechCategory\nProj1\tProjectOnly\tSocial\n")

    loader = InputLoader(tmp_path)
    report = loader.load()
    validator = GraphValidator(report.nodes)
    result = validator.validate()

    assert result.has_errors
    assert any("must depend on at least one tech" in issue.message for issue in result.errors)
