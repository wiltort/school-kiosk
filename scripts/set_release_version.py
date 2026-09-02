#!/usr/bin/env python3
"""Проставляет версию релиза в `src-tauri/Cargo.toml` и `tauri.conf.json`.

Используется в CI перед сборкой, чтобы версия была монотонной внутри канала
(например `0.1.0-dev.42` для канала dev). Меняет только файлы локально —
коммитить их не нужно.

Пример:
    python scripts/set_release_version.py --version 0.1.0-dev.42
"""

import argparse
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
CARGO = ROOT / "src-tauri" / "Cargo.toml"
CONF = ROOT / "src-tauri" / "tauri.conf.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version", required=True, help="Новая версия, например 0.1.0-dev.42"
    )
    args = parser.parse_args()
    version = args.version

    # [package].version в Cargo.toml — первый блок version.
    cargo = CARGO.read_text(encoding="utf-8")
    new_cargo, n = re.subn(
        r'(?m)^version\s*=\s*"[^"]+"', f'version = "{version}"', cargo, count=1
    )
    if n != 1:
        raise SystemExit(f"Не удалось найти version в {CARGO}")
    CARGO.write_text(new_cargo, encoding="utf-8")

    # version в tauri.conf.json (с сохранением форматирования 2 пробела).
    conf = json.loads(CONF.read_text(encoding="utf-8"))
    conf["version"] = version
    CONF.write_text(
        json.dumps(conf, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"Версия установлена: {version}")


if __name__ == "__main__":
    main()
