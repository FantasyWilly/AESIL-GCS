from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install an MBTiles file into this project.")
    parser.add_argument("source", help="Path to the source .mbtiles file")
    parser.add_argument(
        "--dest",
        default="data/offline.mbtiles",
        help="Destination path inside the project (default: data/offline.mbtiles)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = Path(args.source).expanduser().resolve()
    destination = Path(args.dest).expanduser().resolve()

    if not source.exists():
        raise SystemExit(f"Source file does not exist: {source}")
    if source.suffix.lower() != ".mbtiles":
        raise SystemExit(f"Source is not an .mbtiles file: {source}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    print(f"Installed MBTiles to: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
