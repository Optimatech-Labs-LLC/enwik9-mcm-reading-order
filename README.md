# enwik9 MCM in reading order

OptimaTech Labs added reversible Wikipedia-specific predictions ahead of Mathieu Chartier’s MCM 0.83. Articles are compressed in their original sequence. The resulting package is **143,624,805 bytes including the offline source decoder**. It restored all **1,000,000,000 bytes** in **627.776 seconds** on an Intel Xeon Gold 6548N Linux system. The full offline restore passed a byte comparison and SHA-256. [Download v0.1.0](https://github.com/Optimatech-Labs-LLC/enwik9-mcm-reading-order/releases/tag/v0.1.0) · [Upstream MCM](https://github.com/mathieuchartier/mcm/tree/02b4e7d50a39f94d17ab3bf3d49a597a10b1f4a1)

| Full-file measurement | Matched MCM control | Reading-order predictions |
|---|---:|---:|
| Archive bytes | 144,855,293 | 143,517,939 |
| Source decoder ZIP bytes | 102,476 | 106,866 |
| **Total bytes** | **144,957,769** | **143,624,805** |

## What changed

An editor’s name helps predict their numeric ID. Nearby revision IDs help predict a revision timestamp. When the forecast misses, the archive carries an exact correction. The encoder also refers back to repeated article titles and copies text shared by a link destination and its displayed label. Both sides reconstruct those references in reading order.

Our MCM build reads the transformed stream as one text segment using `-x11`. Its normal two-pass dictionary travels inside the archive. The predictions removed 1,337,354 bytes from the archive and added 4,390 bytes to the decoder. The net saving was **1,332,964 bytes** against the same backend without the predictions. [Transform](reader/field_lines.py) · [Build and MCM configuration](build_backend.py)

## Download and restore offline

Use Linux x86-64, CPython 3.12 or later, g++, and the static C and C++ system libraries. The decoder ZIP contains the exact MCM and transform sources used for the measured restore. Run the following in an empty directory.

```sh
release=https://github.com/Optimatech-Labs-LLC/enwik9-mcm-reading-order/releases/download/v0.1.0
curl -fLO "$release/enwik9-reading-order.mcm"
curl -fLO "$release/offline-decoder.zip"
curl -fLO "$release/SHA256SUMS"
sha256sum --check SHA256SUMS
unzip -q offline-decoder.zip -d decoder
python3 decoder/restore.py enwik9-reading-order.mcm enwik9
wc -c enwik9
sha256sum enwik9
```

Expected output is 1,000,000,000 bytes with SHA-256 `159b85351e5f76e60cbe32e04c677847a9ecba3adc79addab6f4c6c7aa3744bc`. If you have the reference corpus, `cmp enwik9 /path/to/reference/enwik9` compares every byte.

## Reproduce the archive

From a checkout, run the encoder on the raw benchmark file. Use a new output path with enough disk space for the input, intermediate transformed data, and output. The backend builds from the included MCM source with the same configuration as the decoder. [Original enwik9 corpus](https://mattmahoney.net/dc/textdata.html)

```sh
python3 encode.py /path/to/enwik9 rebuilt.mcm
echo '5851ffe130393e979c5fc60f626ca7a402258f8c6821927f314ee6e73465d5a7  rebuilt.mcm' | sha256sum --check
```

Preprocessing took 66.46 seconds and MCM compression took 563.19 seconds on a 32-vCPU Intel Xeon Gold 6548N Linux droplet with 256 GiB of installed RAM. A separate restore built the decoder from its ZIP with networking disabled. The 627.776-second restore time includes compilation and decoding. The byte comparison and final SHA-256 were checked afterward. Other trials shared the host. Peak process memory and enwik8 size are unmeasured. [Measurement](benchmark.json)

MCM 0.83 and the release code are provided under GPLv3. The complete pinned upstream source and its COPYING file are in `mcm-0.83.tar.gz`. The Wikipedia corpus carries its own terms. [Software license](LICENSE) · [Attribution and corpus terms](ATTRIBUTION.md)
