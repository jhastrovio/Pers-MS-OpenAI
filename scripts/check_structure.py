"""Project structure and import‑boundary checker.

Run this script from the repo root:

    python scripts/check_structure.py

* exits with 0 if all checks pass
* exits with 1 and prints a list of problems otherwise
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

# Top‑level folders that are allowed in the repo root.
ALLOWED_TOP_LEVEL: set[str] = {
    "core",
    "docs",
    "tests",
    "scripts",  # tooling such as this script
    ".github",  # CI configuration
    ".venv",  # virtualenv (ignored)
    "CHANGELOG.md",
    "README.md",
    "LICENSE",
}

# Regex patterns for versioned core sub‑folders
PATTERNS: Dict[str, re.Pattern[str]] = {
    "api": re.compile(r"api_\d+_\d+_\d+"),
    "graph": re.compile(r"graph_\d+_\d+_\d+"),
    "openai": re.compile(r"openai_\d+_\d+_\d+"),
    "processing": re.compile(r"processing_\d+_\d+_\d+"),
    "storage": re.compile(r"storage_\d+_\d+_\d+"),
    "utils": re.compile(r"utils"),  # non‑versioned
}

# Import‑boundary rules.  Each key is the folder *type* (from PATTERNS), the
# value is a set of *types* that **may** be imported from that folder.
IMPORT_ALLOWED: Dict[str, set[str]] = {
    "api": {"processing", "graph", "openai", "utils"},
    "processing": {"graph", "openai", "storage", "utils"},
    "graph": {"utils"},
    "openai": {"utils"},
    "storage": {"utils"},
    "utils": set(),
}

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def classify_core_subfolder(name: str) -> str | None:
    """Return the logical folder type (api, graph, …) for a core sub‑folder"""
    for f_type, pat in PATTERNS.items():
        if pat.fullmatch(name):
            return f_type
    return None


def iter_python_files(root: Path) -> List[Path]:
    """Yield all *.py files under *root* excluding virtualenv & hidden dirs."""
    ignored = {".venv", "__pycache__", ".git", ".mypy_cache"}
    return [
        p
        for p in root.rglob("*.py")
        if not any(part in ignored for part in p.parts)
    ]


def validate_top_level(root: Path) -> List[str]:
    """Check that only allowed folders/files exist at repo root."""
    errors: List[str] = []
    for item in root.iterdir():
        if item.name.startswith(".") and item.name not in {".github", ".venv"}:
            # allow dotfiles generically except unknown dirs
            continue
        if item.name not in ALLOWED_TOP_LEVEL and not item.name.endswith(
            (".md", ".toml", ".yml", ".yaml")
        ):
            errors.append(f"Disallowed top‑level item: {item}")
    return errors


def validate_core_structure(root: Path) -> List[str]:
    """Ensure every direct child of core/ matches an approved pattern."""
    errors: List[str] = []
    core_dir = root / "core"
    if not core_dir.exists():
        errors.append("Missing required folder: core/")
        return errors
    for sub in core_dir.iterdir():
        if not sub.is_dir():
            continue
        if classify_core_subfolder(sub.name) is None:
            errors.append(f"Invalid core sub‑folder name: {sub.name}")
    return errors


def imports_in_file(path: Path) -> List[str]:
    """Return a list of imported module strings inside *path*."""
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        # Skip files with syntax errors (they'll be caught by flake8/pytest)
        return []
    names: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.append(node.module)
    return names


def validate_import_boundaries(root: Path) -> List[str]:
    """Ensure files do not import disallowed core modules."""
    errors: List[str] = []
    for pyfile in iter_python_files(root / "core"):
        rel_parts = pyfile.relative_to(root).parts
        if len(rel_parts) < 2:
            continue  # should not happen
        core_sub = rel_parts[1]
        src_type = classify_core_subfolder(core_sub)
        if not src_type:
            continue
        allowed = IMPORT_ALLOWED[src_type]
        for mod in imports_in_file(pyfile):
            if not mod.startswith("core."):
                continue
            tgt_sub = mod.split(".")[1]
            tgt_type = classify_core_subfolder(tgt_sub)
            if tgt_type is None:
                continue  # unknown pattern; structure check will flag
            if tgt_type not in allowed and tgt_type != src_type:
                errors.append(
                    f"❌  {pyfile}: cannot import '{mod}' (rule: {src_type} may not import {tgt_type})"
                )
    return errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent

    problems: List[Tuple[str, List[str]]] = []
    for name, checker in (
        ("Top‑level items", validate_top_level),
        ("Core folder names", validate_core_structure),
        ("Import boundaries", validate_import_boundaries),
    ):
        errs = checker(repo_root)
        if errs:
            problems.append((name, errs))

    if problems:
        print("\nSTRUCTURE CHECK FAILED\n" + "-" * 30)
        for section, errs in problems:
            print(f"\n[{section}]")
            for e in errs:
                print("  ", e)
        print("\nFix the above issues or update rules in scripts/check_structure.py")
        sys.exit(1)
    else:
        print("✅  Structure check passed.")


if __name__ == "__main__":
    main()
