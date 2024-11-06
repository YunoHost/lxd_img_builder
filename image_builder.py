#!/usr/bin/env python3

import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from incuslib import Incus, SimpleStreams


SCRIPT_DIR = Path(__file__).resolve().parent

incus = Incus()


class ImageBuilder:
    def __init__(
        self, debian_version: str, distribution: str, ss_repo: Path, log: Optional[Path]
    ) -> None:
        self.debian_version = debian_version
        self.distribution = distribution
        self.instance_name = f"ynh-builder-{self.debian_version}-{self.distribution}"
        self.ss_repo = ss_repo
        self.log = log

    def image_alias(self, short_name: str) -> str:
        return f"yunohost/{self.debian_version}-{self.distribution}/{short_name}"

    def start(self, base_image_name: Optional[str] = None) -> None:
        if base_image_name is None:
            base_image_name = f"images:debian/{self.debian_version}"
        self.clear()
        incus.launch(base_image_name, self.instance_name)

        # 240501: fix because the container was not getting an IP
        incus.execute(self.instance_name, "dhclient", "eth0")

    def clear(self) -> None:
        if not incus.instance_exists(self.instance_name):
            return

        logging.info("Deleting existing container...")
        if not incus.instance_stopped(self.instance_name):
            incus.instance_stop(self.instance_name)
        incus.instance_delete(self.instance_name)

    def publish(self, short_name: str) -> None:
        should_restart = False
        self.run_script("slimify")

        image_alias = self.image_alias(short_name)

        arch = incus.arch()
        now = datetime.now()
        image_descr = f"YunoHost {self.debian_version} {self.distribution} ynh-{short_name} {arch} ({now:%Y%m%d})"

        if incus.image_exists(image_alias):
            logging.info(f"Deleting already existing image {image_alias}")
            incus.image_delete(image_alias)

        if not incus.instance_stopped(self.instance_name):
            should_restart = True
            incus.instance_stop(self.instance_name)

        properties = {
            "description": image_descr,
            "os": "yunohost",
            "release": f"{self.debian_version}-{self.distribution}",
            "variant": short_name,
            "architecture": arch,
        }

        logging.info(f"Publishing {image_alias}...")
        incus.publish(self.instance_name, image_alias, properties)

        if self.ss_repo:
            ss = SimpleStreams(incus, self.ss_repo, SCRIPT_DIR / "images")
            ss.import_from_incus(image_alias, image_alias)

        if should_restart:
            incus.instance_start(self.instance_name)
            # 240501: fix because the container was not getting an IP
            incus.execute(self.instance_name, "dhclient", "eth0")

    def put_file(self, file: Path, dest_file: str) -> None:
        logging.info(f"Pushing {file} to {dest_file}...")
        incus.push_file(self.instance_name, file, dest_file)

    def run(self) -> None:
        incus.execute(self.instance_name, "ls", "-lah")

    def run_script(self, name: str) -> None:
        self.put_file(SCRIPT_DIR / "recipes", "/root/recipes")

        gitbranch = "dev" if self.debian_version == "bookworm" else self.debian_version
        command = [
            "env",
            f"RELEASE={self.distribution}",
            f"DEBIAN_VERSION={self.debian_version}",
            f"gitbranch={gitbranch}",
            "/root/recipes",
            name,
        ]
        logging.info("Running: %s...", " ".join(command))
        incus.execute(self.instance_name, *command)

        incus.execute(self.instance_name, "rm", "/root/recipes")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        required=False,
        help="If passed, the path to the simplestreams repository",
    )
    parser.add_argument(
        "-l",
        "--log",
        type=Path,
        required=False,
        help="If passed, logs will be printed to this file",
    )

    parser.add_argument("debian_version", type=str, choices=["bullseye", "bookworm"])
    parser.add_argument(
        "distribution", type=str, choices=["stable", "testing", "unstable"]
    )
    parser.add_argument(
        "variants",
        type=str,
        choices=["build-and-lint", "before-install", "appci-only", "all", "demo"],
    )
    args = parser.parse_args()

    logger = logging.getLogger()
    if args.log:
        logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(args.log)
        fh.setLevel(logging.DEBUG)
        logger.addHandler(fh)
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        logger.addHandler(console)
    else:
        logger.setLevel(logging.DEBUG)

    logging.debug("Starting at %s", datetime.now())

    builder = ImageBuilder(
        args.debian_version, args.distribution, args.output, args.log
    )

    if args.variants == "build-and-lint":
        builder.start()
        builder.put_file(
            SCRIPT_DIR / "gitlab-runner-light.deb", "/root/gitlab-runner-light.deb"
        )
        builder.run_script("build_and_lint")
        builder.publish("build-and-lint")

    if args.variants == "before-install":
        builder.start()
        builder.put_file(
            SCRIPT_DIR / "gitlab-runner-light.deb", "/root/gitlab-runner-light.deb"
        )
        builder.run_script("before_install")
        builder.publish("before-install")

    if args.variants == "all":
        builder.start()
        builder.put_file(
            SCRIPT_DIR / "gitlab-runner-light.deb", "/root/gitlab-runner-light.deb"
        )
        builder.run_script("dev")
        builder.publish("dev")
        builder.run_script("appci")
        builder.publish("appci")
        builder.run_script("core_tests")
        builder.publish("core-tests")

    if args.variants == "appci-only":
        # Start back from dev image
        builder.start(builder.image_alias("dev"))
        builder.run_script("appci")
        builder.publish("appci")

    if args.variants == "demo":
        builder.start(builder.image_alias("before-install"))
        builder.run_script("demo")
        builder.publish("demo")

    builder.clear()


if __name__ == "__main__":
    main()
