
"""
Pad the edges of Python files with exactly one blank line at the top and exactly one newline
after the last line of code. Ruff's formatter strips leading blank lines, so it can't do this.

Usage: python scripts/format_file_edges.py [--check] PATH...
"""

import argparse
import sys

from pathlib import Path


def format_edges(source: str) -> str:
    body = source.strip()
    if not body:
        # Leave empty files (e.g. __init__.py) empty
        return source
    return f"\n{body}\n"


def iter_python_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        files.extend(sorted(path.rglob("*.py")) if path.is_dir() else [path])
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="report files that need changes without writing them")
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    changed: list[Path] = []
    for file in iter_python_files(args.paths):
        source = file.read_text()
        formatted = format_edges(source)
        if formatted == source:
            continue
        changed.append(file)
        if not args.check:
            file.write_text(formatted)

    for file in changed:
        print(f"{'Would reformat' if args.check else 'Reformatted'}: {file}")
    if args.check and changed:
        print(f"{len(changed)} file(s) need edge formatting. Run: python scripts/format_file_edges.py <paths>")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
