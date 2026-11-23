"""Build a single-stream text-only MCM from its pinned source archive on Linux."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
import argparse
import subprocess
import tarfile

PIN = "02b4e7d50a39f94d17ab3bf3d49a597a10b1f4a1"
SOURCE_SHA = "af45019a3ce43c7560f274516f974b08bcae27de6fca5fec40e112cc046f231e"


def build(tar, work):
    assert sha256(tar.read_bytes()).hexdigest() == SOURCE_SHA
    work.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tar) as archive:
        archive.extractall(work, filter="data")
    src = work / ("mcm-" + PIN)
    detector = src / "Detector.hpp"
    data = detector.read_bytes()
    start = data.index(b"\t\tDetector detector(stream);", data.index(b"\tvoid analyze(Stream*"))
    end = data.index(b"\n\t}\n\tvoid dump()", start)
    # One forward dictionary pass and exactly one text segment. The backend never
    # reorders regions or pages by its ordinary text/binary file classifier.
    body = b"""    uint8_t buffer[65536];
    uint64_t total = 0;
    size_t size;
    while ((size = stream->read(buffer, sizeof(buffer))) != 0) {
      for (size_t i = 0; i < size; ++i) dict_builder_.addChar(buffer[i]);
      total += size;
    }
    if (total == 0 || total > UINT32_MAX) std::abort();
    blocks_.push_back(Detector::DetectedBlock(Detector::kProfileText, uint32_t(total)));"""
    detector.write_bytes(data[:start] + body + data[end:])
    units = "CM Archive Huffman MCM Memory Util Compressor LZ".split()
    def compile_one(unit):
        subprocess.run(["g++", "-w", "-O3", "-std=gnu++11", "-msse2", "-DNDEBUG", "-D_FILE_OFFSET_BITS=64",
                        "-ffunction-sections", "-fdata-sections", "-c", str(src / (unit + ".cpp")),
                        "-o", str(work / (unit + ".o"))], check=True)
    with ThreadPoolExecutor(8) as pool:
        list(pool.map(compile_one, units))
    subprocess.run(["g++", "-static", "-s", "-Wl,--gc-sections", "-o", str(work / "mcm-text"),
                    *(str(work / (k + ".o")) for k in units), "-lpthread"], check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_tar", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build(args.source_tar.resolve(), args.output.resolve())
