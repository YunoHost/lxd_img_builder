#!/usr/bin/env python3

import argparse
import os
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import IO, Any, Optional

import yaml


SCRIPT_DIR = Path(__file__).resolve().parent


class Incus:
    def __init__(self) -> None:
        pass

    def arch(self) -> str:
        plat = platform.machine()
        if plat in ["x86_64", "amd64"]:
            return "amd64"
        if plat in ["arm64", "aarch64"]:
            return "arm64"
        if plat in ["armhf"]:
            return "armhf"
        raise RuntimeError(f"Unknown platform {plat}!")

    def _run(self, *args: str, capture: bool = True, **kwargs) -> str:
        command = ["incus"] + [*args]
        if capture:
            return subprocess.check_output(command, **kwargs).decode("utf-8")
        else:
            subprocess.run(
                command, stdout=sys.stdout, stderr=sys.stderr, check=True, **kwargs
            )
            return ""

    # def _run_popen(self, *args: str) -> subprocess.Popen:
    #     command = ["incus"] + [*args]
    #     proc = subprocess.Popen(command, stdout=sys.stdout, stderr=sys.stderr,
    #                             #, text=True, bufsize=1, close_fds=True
    #                             )
    #     return proc

    def instance_stopped(self, name: str) -> bool:
        assert self.instance_exists(name)
        res = yaml.safe_load(self._run("info", name))
        return res["Status"] == "STOPPED"

    def instance_exists(self, name: str) -> bool:
        res = yaml.safe_load(self._run("list", "-f", "yaml"))
        instance_names = [instance["name"] for instance in res]
        return name in instance_names

    def instance_start(self, name: str) -> None:
        self._run("start", name)

    def instance_stop(self, name: str) -> None:
        self._run("stop", name)

    def instance_delete(self, name: str) -> None:
        self._run("delete", name)

    def launch(self, image_name: str, instance_name: str) -> None:
        self._run("launch", image_name, instance_name)

    def push_file(self, instance_name: str, file: Path, target: str) -> None:
        self._run("file", "push", str(file), f"{instance_name}{target}")
        os.sync()

    def execute(self, instance_name: str, *args: str) -> None:
        self._run("exec", instance_name, "--", *args, capture=False)
        return
        proc = self._run_popen("exec", instance_name, "--", *args)

        def print_io(stream: IO[Any]):
            for line in stream:
                print(" In container |\t", line.strip())

        while proc.poll() is None:
            assert proc.stdout is not None
            assert proc.stderr is not None
            print_io(proc.stderr)
            print_io(proc.stdout)

        if proc.returncode:
            raise RuntimeError(f"Could not run incus {args}")

    def publish(
        self, instance_name: str, image_alias: str, properties: dict[str, str]
    ) -> None:
        properties_list = [f"{key}={value}" for key, value in properties.items()]
        self._run("publish", instance_name, "--alias", image_alias, *properties_list)

    def image_export(self, image_alias: str, target_dir: Path) -> None:
        self._run("image", "export", image_alias, image_alias, cwd=target_dir)

    def image_exists(self, alias: str) -> bool:
        res = yaml.safe_load(self._run("image", "list", "-f", "yaml"))
        image_aliases = [alias["name"] for image in res for alias in image["aliases"]]
        return alias in image_aliases

    def image_delete(self, alias: str) -> None:
        self._run("image", "delete", alias)


incus = Incus()


class ImageBuilder:
    def __init__(self, debian_version: str, distribution: str, ss_repo: Path) -> None:
        self.debian_version = debian_version
        self.distribution = distribution
        self.instance_name = f"ynh-builder-{self.debian_version}-{self.distribution}"
        self.ss_repo = ss_repo

    def image_alias(self, short_name: str) -> str:
        return f"ynh-{short_name}-{self.debian_version}-{self.distribution}-base"

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

        print("Deleting existing container...")
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
            print(f"Deleting already existing image {image_alias}")
            incus.image_delete(image_alias)

        if not incus.instance_stopped(self.instance_name):
            should_restart = True
            incus.instance_stop(self.instance_name)

        properties = {
            "description": image_descr,
            "os": "yunohost",
            "release": self.debian_version,
            "variant": f"{self.distribution}-{short_name}",
            "ynh-release": self.distribution,
            "stage": f"ynh-{short_name}",
            "architecture": arch,
        }

        print(f"Publishing {image_alias}...")
        incus.publish(self.instance_name, image_alias, properties)

        images_path = SCRIPT_DIR / "images"
        images_path.mkdir(exist_ok=True)
        image_file = images_path / f"{image_alias}.tar.gz"
        incus.image_export(image_alias, images_path)

        subprocess.run(
            ["incus-simplestreams", "add", image_file],
            cwd=self.ss_repo,
        )
        image_file.unlink()

        if should_restart:
            incus.instance_start(self.instance_name)
            # 240501: fix because the container was not getting an IP
            incus.execute(self.instance_name, "dhclient", "eth0")

    def put_file(self, file: Path, dest_file: str) -> None:
        print(f"Pushing {file} to {dest_file}...")
        incus.push_file(self.instance_name, file, dest_file)

    def run(self) -> None:
        incus.execute(self.instance_name, "ls", "-lah")

    def run_script(self, name: str) -> None:
        gitbranch = "dev" if self.debian_version == "bullseye" else self.debian_version

        # Ensure the file is deleted
        incus.execute(self.instance_name, "rm", "-f", "/root/recipes")
        self.put_file(SCRIPT_DIR / "recipes", "/root/recipes")
        incus.execute(
            self.instance_name,
            "env",
            f"RELEASE={self.distribution}",
            f"DEBIAN_VERSION={self.debian_version}",
            f"gitbranch={gitbranch}",
            "/root/recipes",
            name,
        )

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

    parser.add_argument("debian_version", type=str, choices=["bullseye", "bookworm"])
    parser.add_argument(
        "distribution", type=str, choices=["stable", "testing", "unstable"]
    )
    parser.add_argument(
        "variants", type=str, choices=["build-and-lint", "before-install", "appci-only", "all"]
    )
    args = parser.parse_args()

    builder = ImageBuilder(args.debian_version, args.distribution, args.output)

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

    builder.clear()


if __name__ == "__main__":
    main()
