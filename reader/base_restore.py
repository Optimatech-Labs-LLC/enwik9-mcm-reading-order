"""Usage: python3 restore.py ARCHIVE OUTPUT (Linux x86-64, offline)."""
import argparse
import ctypes as C
import mmap
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def decompress_zstd(codec, data, output):
    lib = C.CDLL(str(codec))
    lib.ZSTD_getFrameContentSize.argtypes = [C.c_void_p, C.c_size_t]
    lib.ZSTD_getFrameContentSize.restype = C.c_ulonglong
    lib.ZSTD_decompress.argtypes = [C.c_void_p, C.c_size_t, C.c_void_p, C.c_size_t]
    lib.ZSTD_decompress.restype = C.c_size_t
    frame = data.read_bytes()
    n = lib.ZSTD_getFrameContentSize(frame, len(frame))
    if not 0 < n < 0xffffffff:
        raise ValueError("unknown or oversized Zstandard frame")
    with output.open("w+b") as f:
        f.truncate(n)
        with mmap.mmap(f.fileno(), n, access=mmap.ACCESS_WRITE) as buf:
            ptr = C.addressof(C.c_char.from_buffer(buf))
            if lib.ZSTD_decompress(ptr, n, frame, len(frame)) != n:
                raise ValueError("incorrect Zstandard output length")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    archive, output = args.archive.resolve(), args.output.resolve()
    if output.exists():
        raise FileExistsError(output)
    with tempfile.TemporaryDirectory(dir=output.parent) as scratch:
        temp = Path(scratch)
        wire = temp / "stream"
        if (root / "mcm-text").is_file():
            (temp / "archive").symlink_to(archive)
            subprocess.run([root / "mcm-text", "d", "archive", "stream"], cwd=temp, check=True)
        else:
            decompress_zstd(root / "libzstd.so.1", archive, wire)
        if (root / "line_inverse.py").is_file():
            from line_inverse import restore
            restored = temp / "output"
            restore(wire, restored)
            os.replace(restored, output)
        else:
            shutil.move(wire, output)


if __name__ == "__main__":
    main()
