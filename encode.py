"""Encode enwik9 in reading order with the transform and MCM sources in the decoder ZIP."""

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from build_backend import build

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "reader"))
from field_lines import convert


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("input", type=Path)
    cli.add_argument("output", type=Path)
    args = cli.parse_args()
    source = args.input.resolve(strict=True)
    target = args.output.absolute()
    if os.path.lexists(target):
        raise FileExistsError(target)
    with tempfile.TemporaryDirectory(dir=target.parent) as tmp:
        stage = Path(tmp)
        backend = stage / "build"
        build(ROOT / "mcm-0.83.tar.gz", backend)
        convert(source, stage / "stream", True)
        subprocess.run([backend / "mcm-text", "-x11", "stream", "archive.mcm"],
                       cwd=stage, check=True)
        os.link(stage / "archive.mcm", target)


if __name__ == "__main__":
    main()
