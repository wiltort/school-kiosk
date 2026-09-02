"""Вывод справки по командам Makefile (для `make help`)."""

import re
import sys
from pathlib import Path

MAKEFILE = Path(__file__).resolve().parent.parent / "Makefile"

# (заголовок, список имён целей / None = все оставшиеся) — секции справки
SECTIONS = [
    ("Project", ["build", "run", "install"]),
    (
        "Frontend",
        ["install-frontend", "run-frontend", "lint-frontend", "format-frontend"],
    ),
    (
        "Backend",
        [
            "build-backend",
            "install-backend",
            "run-backend",
            "test",
            "test-integration",
            "test-coverage",
            "lint",
            "format",
            "check",
        ],
    ),
    ("Tauri (Rust)", ["install-tauri", "lint-rust"]),
    ("Updater", ["update-keys", "update-version"]),
    ("Database", ["db-migration", "db-migrate", "db-migrate-downgrade", "db-current"]),
    ("GitFlow", ["pre-commit-install", "pre-commit", "new-branch"]),
    ("Help", ["help"]),
]

lines = MAKEFILE.read_text(encoding="utf-8")
targets = re.findall(r"^([a-zA-Z_-]+):.*?## (.*)$", lines, re.MULTILINE)

out = sys.stdout
for title, names in SECTIONS:
    out.write(f"\n  \033[1;33m{title}\033[0m\n")
    for name, doc in targets:
        if names is None or name in names:
            out.write(f"  \033[36m{name:<20}\033[0m {doc}\n")
