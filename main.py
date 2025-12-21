from pathlib import Path

from terra_invicta_tech_optimizer import GraphValidator, InputLoader


def main():
    input_dir = Path(__file__).parent / "inputs"
    loader = InputLoader(input_dir)
    load_report = loader.load()

    if load_report.errors:
        print("Encountered errors while loading inputs:")
        for error in load_report.errors:
            print(f"- {error}")
        return

    print(f"Loaded {len(load_report.nodes)} nodes from {input_dir}.")
    for warning in load_report.warnings:
        print(f"Warning: {warning}")

    validator = GraphValidator(load_report.nodes)
    validation_result = validator.validate()

    if validation_result.has_errors:
        print("Validation failed:")
        for issue in validation_result.errors:
            node_list = ", ".join(issue.nodes)
            print(f"- {issue.message} (nodes: {node_list})")
    else:
        print("Validation successful. No issues detected.")


if __name__ == "__main__":
    main()
