#!/usr/bin/env python3

import argparse
from pathlib import Path

from incuslib import Incus, SimpleStreams

SCRIPT_DIR = Path(__file__).resolve().parent

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

    incus = Incus()
    ss = SimpleStreams(incus, args.repository, SCRIPT_DIR / "images")
    ss.clean_previous_versions()
    ss.prune_images()


if __name__ == "__main__":
    main()
