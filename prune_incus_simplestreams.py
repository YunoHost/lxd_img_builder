#!/usr/bin/env python3

import argparse
import subprocess
from pathlib import Path
import json


def images_paths(repo_root: Path, images_data: dict) -> list[str]:
    images = [
        repo_root / item["path"]
        for product in images_data["products"].values()
        for version in product["versions"].values()
        for item in version["items"].values()
    ]
    return images


def clean_old_versions(repo_root: Path, images_data: dict) -> None:
    for product_name, product in images_data["products"].items():
        versions = sorted(product["versions"].keys())
        for version in versions[:-1]:
            for item in product["versions"][version]["items"].values():
                sha = item["sha256"]
                print(f"Pruning {product_name} / {sha}...")
                subprocess.run(["incus-simplestreams", "remove", sha], cwd=repo_root)


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

    images_file = args.repository / "streams" / "v1" / "images.json"
    images_data = json.load(images_file.open(encoding="utf-8"))

    images = images_paths(args.repository, images_data)

    images_dir: Path = args.repository / "images"
    for file in images_dir.iterdir():
        if file not in images:
            print(f"Pruning {file.name}...")
            file.unlink()

    clean_old_versions(args.repository, images_data)


if __name__ == "__main__":
    main()
