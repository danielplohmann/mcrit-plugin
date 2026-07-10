import argparse
import json
import re
import sys
from pathlib import Path


def extract_config_version(config_path: Path) -> str:
    match = re.search(
        r'^VERSION = "([^"]+)"', config_path.read_text(encoding="utf-8"), re.MULTILINE
    )
    if not match:
        raise ValueError(f"Could not find VERSION in {config_path}")
    return match.group(1)


def extract_readme_release_version(readme_path: Path) -> str:
    match = re.search(
        r"^### v(\d+\.\d+\.\d+)\b", readme_path.read_text(encoding="utf-8"), re.MULTILINE
    )
    if not match:
        raise ValueError(f"Could not find latest release heading in {readme_path}")
    return match.group(1)


def extract_readme_min_ida_version(readme_path: Path) -> str:
    text = readme_path.read_text(encoding="utf-8")
    patterns = [
        r"badge/IDA-(\d+(?:\.\d+)?)%2B",
        r"\bIDA (\d+(?:\.\d+)?)\+",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    raise ValueError(f"Could not determine README minimum IDA version from {readme_path}")


def extract_plugin_min_ida_version(value: str) -> str:
    match = re.search(r">=\s*(\d+(?:\.\d+)?)", value)
    if not match:
        raise ValueError(f"Unsupported plugin idaVersions format: {value}")
    return match.group(1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="Path to the repository root")
    parser.add_argument(
        "--expected-version",
        help="Optional semantic version that config.py, ida-plugin.json, and README must all match",
    )
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    config_path = repo / "config.py"
    plugin_path = repo / "ida-plugin.json"
    readme_path = repo / "README.md"

    plugin_data = json.loads(plugin_path.read_text(encoding="utf-8"))
    config_version = extract_config_version(config_path)
    plugin_version = plugin_data["plugin"]["version"]
    readme_version = extract_readme_release_version(readme_path)
    plugin_min_ida = extract_plugin_min_ida_version(plugin_data["plugin"]["idaVersions"])
    readme_min_ida = extract_readme_min_ida_version(readme_path)

    print(f"[INFO] config.py VERSION: {config_version}")
    print(f"[INFO] ida-plugin.json plugin.version: {plugin_version}")
    print(f"[INFO] README latest release version: {readme_version}")
    print(f"[INFO] ida-plugin.json minimum IDA version: {plugin_min_ida}")
    print(f"[INFO] README top-level minimum IDA version: {readme_min_ida}")

    failures: list[str] = []
    if config_version != readme_version:
        failures.append(
            "Version mismatch: config.py VERSION does not match latest README release heading."
        )
    if plugin_version != readme_version:
        failures.append(
            "Version mismatch: ida-plugin.json plugin.version does not match latest README release heading."
        )
    if plugin_min_ida != readme_min_ida:
        failures.append(
            "IDA compatibility mismatch: ida-plugin.json plugin.idaVersions and README top-level compatibility badge/text are inconsistent."
        )

    if args.expected_version:
        if config_version != args.expected_version:
            failures.append(
                f"Version mismatch: config.py VERSION does not match expected version {args.expected_version}."
            )
        if plugin_version != args.expected_version:
            failures.append(
                f"Version mismatch: ida-plugin.json plugin.version does not match expected version {args.expected_version}."
            )
        if readme_version != args.expected_version:
            failures.append(
                f"Version mismatch: README latest release heading does not match expected version {args.expected_version}."
            )

    if failures:
        print("[FAIL] Metadata consistency checks failed:")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("[PASS] Metadata consistency checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
