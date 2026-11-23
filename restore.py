"""Restore offline using the included MCM sources. Requires Linux x86-64, Python 3.12+ and g++."""
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess
import sys
from build_backend import build


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: python3 restore.py ARCHIVE OUTPUT")
    root = Path(__file__).resolve().parent
    archive, target = (Path(arg).resolve() for arg in sys.argv[1:])
    if target.exists():
        raise FileExistsError(target)
    with TemporaryDirectory(dir=target.parent) as path:
        scratch = Path(path)
        build(root / "mcm-0.83.tar.gz", scratch / "build")
        runtime = scratch / "reader"
        shutil.copytree(root / "reader", runtime)
        (runtime / "mcm-text").symlink_to(scratch / "build/mcm-text")
        subprocess.run([sys.executable, runtime / "restore.py", archive, target], check=True)


if __name__ == "__main__":
    main()
