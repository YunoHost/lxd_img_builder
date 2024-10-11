#!/usr/bin/env python3

import argparse
from pathlib import Path
import json


def images_paths(repo: Path) -> list[str]:
    images_file = repo / "streams" / "v1" / "images.json"
    images_data = json.load(images_file.open(encoding="utf-8"))

    images = [
        repo / item["path"]
        for product in images_data["products"].values()
        for version in product["versions"].values()
        for item in version["items"].values()
    ]
    return images


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-r",
        "--repository",
        type=Path,
        required=True,
        help="The path to the simplestreams repository",
    )
    args = parser.parse_args()

    images = images_paths(args.repository)

    images_dir: Path = args.repository / "images"
    for file in images_dir.iterdir():
        if file not in images:
            print(f"Pruning {file.name}...")
            file.unlink()


if __name__ == "__main__":
    main()
