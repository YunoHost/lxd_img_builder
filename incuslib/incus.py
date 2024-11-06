#!/usr/bin/env python3

import logging
import os
import platform
import subprocess
from pathlib import Path

import yaml


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

    def _run(self, *args: str, **kwargs) -> str:
        command = ["incus"] + [*args]
        return subprocess.check_output(command, **kwargs).decode("utf-8")

    def _run_logged_prefixed(self, *args: str, prefix: str = "", **kwargs) -> None:
        command = ["incus"] + [*args]

        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs
        )
        assert process.stdout
        with process.stdout:
            for line in iter(process.stdout.readline, b""):  # b'\n'-separated lines
                logging.debug("%s%s", prefix, line.decode("utf-8").rstrip("\n"))
        exitcode = process.wait()  # 0 means success
        if exitcode:
            raise RuntimeError(f"Could not run {' '.join(command)}")

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
        self._run_logged_prefixed(
            "exec", instance_name, "--", *args, prefix=" In container |\t"
        )

    def publish(
        self, instance_name: str, image_alias: str, properties: dict[str, str]
    ) -> None:
        properties_list = [f"{key}={value}" for key, value in properties.items()]
        self._run("publish", instance_name, "--alias", image_alias, *properties_list)

    def image_export(
        self, image_alias: str, image_target: str, target_dir: Path
    ) -> None:
        self._run("image", "export", image_alias, image_target, cwd=target_dir)

    def image_exists(self, alias: str) -> bool:
        res = yaml.safe_load(self._run("image", "list", "-f", "yaml"))
        image_aliases = [alias["name"] for image in res for alias in image["aliases"]]
        return alias in image_aliases

    def image_delete(self, alias: str) -> None:
        self._run("image", "delete", alias)
