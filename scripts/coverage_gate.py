from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load_coverage_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"coverage json not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid coverage json: {path}: {exc}") from exc


def _pct(value: object) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise SystemExit(f"invalid percent value: {value!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Fail the build if total or per-file test coverage is below threshold. "
            "Input must be pytest-cov's JSON report (coverage.json)."
        )
    )
    parser.add_argument("coverage_json", type=Path)
    parser.add_argument("--total-threshold", type=float, required=True)
    parser.add_argument("--per-file-threshold", type=float, required=True)

    args = parser.parse_args(argv)

    data = _load_coverage_json(args.coverage_json)

    totals = data.get("totals", {})
    total_pct = _pct(
        totals.get("percent_covered", totals.get("percent_covered_display"))
    )

    failures: list[str] = []
    if total_pct + 1e-9 < args.total_threshold:
        failures.append(
            f"TOTAL coverage {total_pct:.2f}% < {args.total_threshold:.2f}%"
        )

    files = data.get("files", {})
    for file_path, file_data in sorted(files.items()):
        summary = (file_data or {}).get("summary", {})
        file_pct = _pct(
            summary.get("percent_covered", summary.get("percent_covered_display"))
        )
        if file_pct + 1e-9 < args.per_file_threshold:
            failures.append(
                f"{file_path}: {file_pct:.2f}% < {args.per_file_threshold:.2f}%"
            )

    if failures:
        print("Coverage gate failed:")
        for msg in failures:
            print(f"- {msg}")
        return 1

    print(
        f"Coverage gate passed (total={total_pct:.2f}%, per-file>={args.per_file_threshold:.2f}%)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
