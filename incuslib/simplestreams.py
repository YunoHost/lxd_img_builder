#!/usr/bin/env python3

import json
import logging
import subprocess
from pathlib import Path

from .incus import Incus


class SimpleStreams:
    def __init__(self, incus: Incus, path: Path, cachedir: Path) -> None:
        self.incus = incus
        self.path = path
        self.path.mkdir(exist_ok=True)
        self.cachedir = cachedir
        self.cachedir.mkdir(exist_ok=True)

    def import_from_incus(self, name: str, alias: str) -> None:
        image_alias_underscorified = alias.replace("/", "_")
        image_file = self.cachedir / f"{image_alias_underscorified}.tar.gz"

        self.incus.image_export(name, image_alias_underscorified, self.cachedir)

        subprocess.run(
            ["incus-simplestreams", "add", image_file],
            cwd=self.path,
        )
        image_file.unlink()

    def images_paths(self) -> list[str]:
        images_data = self.images_data()
        images = [
            self.path / item["path"]
            for product in images_data["products"].values()
            for version in product["versions"].values()
            for item in version["items"].values()
        ]
        return images

    def images_data(self) -> dict:
        images_file = self.path / "streams" / "v1" / "images.json"
        images_data = json.load(images_file.open(encoding="utf-8"))
        return images_data

    def prune_images(self) -> None:
        images_dir: Path = self.path / "images"

        images = self.images_paths()
        for file in images_dir.iterdir():
            if file not in images:
                logging.info(f"Pruning {file.name}...")
                file.unlink()

    def clean_previous_versions(self) -> None:
        for product_name, product in self.images_data()["products"].items():
            versions = sorted(product["versions"].keys())
            for version in versions[:-1]:
                for item in product["versions"][version]["items"].values():
                    sha = item["sha256"]
                    print(f"Pruning {product_name} / {sha}...")
                    subprocess.run(
                        ["incus-simplestreams", "remove", sha], cwd=self.path
                    )
