
"""Command line interface for scaffolding FastAPI apps from this template."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys

from pathlib import Path


DEFAULT_TEMPLATE_REPO = "https://github.com/SteffenCucos/Server_Template.git"
DEFAULT_TEMPLATE_BRANCH = "main"
TEMPLATE_PACKAGE_NAME = "server_template"
TEXT_FILE_SUFFIXES = {
    ".cfg",
    ".env",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}


def main(argv: list[str] | None = None) -> int:
    """Run the server-template CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "new":
            scaffold_new_app(args)
            return 0
    except KeyboardInterrupt:
        print("Aborted.", file=sys.stderr)
        return 130
    except Exception as exc:  # pragma: no cover - keeps CLI errors readable.
        print(f"error: {exc}", file=sys.stderr)
        return 1

    parser.print_help()
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="server-template",
        description="Scaffold a FastAPI service by cloning the Server_Template repository.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    new_parser = subparsers.add_parser(
        "new",
        help="Create a new app from the template.",
        description="Clone the template repo, remove template Git metadata, and rewrite project placeholders.",
    )
    new_parser.add_argument("name", help="Display name for the new app, e.g. billing-api")
    new_parser.add_argument(
        "--target-dir",
        type=Path,
        help="Exact directory to create. Defaults to ./<normalized-name>.",
    )
    new_parser.add_argument(
        "--package-name",
        help="Python package name to use. Defaults to a normalized version of the app name.",
    )
    new_parser.add_argument(
        "--repo",
        default=os.environ.get("SERVER_TEMPLATE_REPO", DEFAULT_TEMPLATE_REPO),
        help=f"Template Git repo URL. Defaults to {DEFAULT_TEMPLATE_REPO}.",
    )
    new_parser.add_argument(
        "--branch",
        default=os.environ.get("SERVER_TEMPLATE_BRANCH", DEFAULT_TEMPLATE_BRANCH),
        help=f"Template branch/tag/ref to clone. Defaults to {DEFAULT_TEMPLATE_BRANCH}.",
    )
    new_parser.add_argument(
        "--keep-git",
        action="store_true",
        help="Keep the cloned .git directory instead of producing a fresh app folder.",
    )
    new_parser.add_argument(
        "--keep-cli",
        action="store_true",
        help="Keep this scaffold CLI in the generated app.",
    )
    new_parser.add_argument(
        "--force",
        action="store_true",
        help="Delete the target directory first if it already exists.",
    )
    return parser


def scaffold_new_app(args: argparse.Namespace) -> None:
    app_name = args.name.strip()
    if not app_name:
        raise ValueError("app name cannot be empty")

    package_name = args.package_name or normalize_package_name(app_name)
    validate_package_name(package_name)

    project_slug = normalize_project_slug(app_name)
    destination = (args.target_dir or Path.cwd() / project_slug).expanduser().resolve()

    prepare_destination(destination, force=args.force)
    clone_template(args.repo, args.branch, destination)

    if not args.keep_git:
        shutil.rmtree(destination / ".git", ignore_errors=True)

    package_dir = rewrite_package(destination, package_name, keep_cli=args.keep_cli)
    rewrite_project_files(destination, app_name, project_slug, package_name, keep_cli=args.keep_cli)

    print(f"Created {app_name} at {destination}")
    print(f"Python package: {package_dir.relative_to(destination)}")
    print("Next steps:")
    print(f"  cd {destination}")
    print("  python -m venv .venv")
    print("  source .venv/bin/activate  # Windows: .venv\\Scripts\\activate")
    print("  pip install -r requirements.txt")
    print("  uvicorn main:app --reload")


def prepare_destination(destination: Path, *, force: bool) -> None:
    if not destination.exists():
        return

    if not force:
        raise FileExistsError(f"target already exists: {destination}. Use --force to replace it.")

    if destination.is_dir():
        shutil.rmtree(destination)
    else:
        destination.unlink()


def clone_template(repo_url: str, branch: str, destination: Path) -> None:
    git = shutil.which("git")
    if git is None:
        raise RuntimeError("git is required to scaffold a new app")

    command = [git, "clone", "--depth", "1"]
    if branch:
        command.extend(["--branch", branch])
    command.extend([repo_url, str(destination)])

    result = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "git clone failed"
        raise RuntimeError(message)


def rewrite_package(destination: Path, package_name: str, *, keep_cli: bool) -> Path:
    original_package = destination / TEMPLATE_PACKAGE_NAME
    package_dir = original_package

    if original_package.exists() and package_name != TEMPLATE_PACKAGE_NAME:
        package_dir = destination / package_name
        if package_dir.exists():
            raise FileExistsError(f"package directory already exists after clone: {package_dir}")
        original_package.rename(package_dir)

    if package_dir.exists() and not keep_cli:
        for file_name in ("cli.py", "__main__.py"):
            (package_dir / file_name).unlink(missing_ok=True)

    init_file = package_dir / "__init__.py"
    if init_file.exists():
        init_file.write_text(
            f'"""{package_name} application package."""\n\n__all__: list[str] = []\n',
            encoding="utf-8",
        )

    return package_dir


def rewrite_project_files(
    destination: Path,
    app_name: str,
    project_slug: str,
    package_name: str,
    *,
    keep_cli: bool,
) -> None:
    for path in destination.rglob("*"):
        if not path.is_file() or should_skip_path(path):
            continue
        if path.suffix.lower() not in TEXT_FILE_SUFFIXES and path.name not in {"Dockerfile"}:
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        text = text.replace("Server Template", app_name)
        text = text.replace("server-template", project_slug)
        text = text.replace(TEMPLATE_PACKAGE_NAME, package_name)
        path.write_text(text, encoding="utf-8")

    rewrite_readme(destination, app_name, package_name)
    rewrite_pyproject(destination, app_name, project_slug, package_name, keep_cli=keep_cli)


def rewrite_readme(destination: Path, app_name: str, package_name: str) -> None:
    readme = destination / "README.md"
    readme.write_text(
        f"""# {app_name}

FastAPI service scaffolded from `SteffenCucos/Server_Template`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

## Run locally

```bash
uvicorn main:app --reload
```

If the application entry point differs, replace `main:app` with the correct module path.

## Project package

```text
{package_name}/
```

## Next work

1. Add endpoint modules.
2. Add domain models.
3. Wire database interfaces or external integrations.
4. Add tests before production use.
""",
        encoding="utf-8",
    )


def rewrite_pyproject(
    destination: Path,
    app_name: str,
    project_slug: str,
    package_name: str,
    *,
    keep_cli: bool,
) -> None:
    pyproject = destination / "pyproject.toml"
    if not pyproject.exists():
        return

    lines = pyproject.read_text(encoding="utf-8").splitlines()
    rewritten: list[str] = []
    current_section: str | None = None
    skip_section = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current_section = stripped
            skip_section = stripped == "[project.scripts]" and not keep_cli
            if not skip_section:
                rewritten.append(line)
            continue

        if skip_section:
            continue

        if current_section == "[project]" and line.startswith("name = "):
            rewritten.append(f'name = "{project_slug}"')
        elif current_section == "[project]" and line.startswith("description = "):
            rewritten.append(f'description = "{app_name} FastAPI service."')
        elif current_section == "[project.scripts]" and keep_cli:
            rewritten.append(line.replace(TEMPLATE_PACKAGE_NAME, package_name))
        elif current_section == "[tool.setuptools.packages.find]":
            rewritten.append(line.replace(TEMPLATE_PACKAGE_NAME, package_name))
        else:
            rewritten.append(line)

    pyproject.write_text("\n".join(rewritten).rstrip() + "\n", encoding="utf-8")


def should_skip_path(path: Path) -> bool:
    skip_parts = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
    return any(part in skip_parts for part in path.parts)


def normalize_project_slug(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", name.strip()).strip(".-_").lower()
    if not slug:
        raise ValueError("could not derive a project directory from the app name")
    return slug


def normalize_package_name(name: str) -> str:
    package_name = re.sub(r"\W+", "_", name.strip().lower()).strip("_")
    if not package_name:
        raise ValueError("could not derive a Python package name from the app name")
    if package_name[0].isdigit():
        package_name = f"app_{package_name}"
    return package_name


def validate_package_name(package_name: str) -> None:
    if not package_name.isidentifier():
        raise ValueError(f"invalid Python package name: {package_name!r}")


if __name__ == "__main__":
    raise SystemExit(main())
