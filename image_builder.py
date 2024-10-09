#!/usr/bin/env python3

import sys
import argparse
from pathlib import Path
import lxd


IMAGES = [
    "build-and-lint",
    "dev",
    "appci",
    "core-tests",
]

# distributions passed to the install script
DISTRIBUTION = ["stable", "testing", "unstable"]

DEBIAN_VERSIONS = ["bullseye", "bookworm"]






def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", type=Path, required=False,
                        help="If passed, the path to the simplestreams repository")

    parser.add_argument("image", type=str, choices=IMAGES)
    parser.add_argument("distribution", type=str, choices=DISTRIBUTION)
    parser.add_argument("debian_version", type=str, choices=DEBIAN_VERSIONS)

    args = parser.parse_args()



if __name__ == "__main__":
    main()
