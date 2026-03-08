import argparse
import json
import sys
import zipfile
from pathlib import Path

INCLUDE_PATHS = [
    "config.py",
    "config_override.json.template",
    "ida-plugin.json",
    "ida_mcrit.py",
    "LICENSE",
    "README.md",
    "helpers",
    "icons",
    "widgets",
]

EXCLUDE_DIR_NAMES = {
    "__pycache__",
}

EXCLUDE_SUFFIXES = {
    ".pyc",
    ".pyo",
}


def should_include(path: Path) -> bool:
    if any(part in EXCLUDE_DIR_NAMES for part in path.parts):
        return False
    if path.suffix in EXCLUDE_SUFFIXES:
        return False
    return True


def iter_files(root: Path, relative_path: str) -> list[Path]:
    source_path = root / relative_path
    if not source_path.exists():
        raise FileNotFoundError(f"Required packaging path is missing: {source_path}")

    if source_path.is_file():
        return [source_path]

    return sorted(
        path for path in source_path.rglob("*") if path.is_file() and should_include(path)
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a minimal ZIP archive for the MCRIT IDA plugin."
    )
    parser.add_argument("--repo", required=True, help="Path to the repository root")
    parser.add_argument("--output", required=True, help="Path to the output ZIP file")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    plugin_name = json.loads((repo / "ida-plugin.json").read_text(encoding="utf-8"))["plugin"][
        "name"
    ]
    written_files: list[str] = []

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative_path in INCLUDE_PATHS:
            for source_path in iter_files(repo, relative_path):
                arcname = source_path.relative_to(repo).as_posix()
                archive.write(source_path, arcname)
                written_files.append(arcname)

    print(f"[INFO] Packaged plugin: {plugin_name}")
    print(f"[INFO] Output archive: {output}")
    print(f"[INFO] Files written: {len(written_files)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
