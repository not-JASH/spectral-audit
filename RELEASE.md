# v0.1.0a2 source preview

Prepared 2026-10-30 from the comparison increment at `cde8240e165de3c9923c86ef3455311ddd3ed7ba`, plus the narrow archive-provenance correction and release preparation. Its final release commit is the source identified by `v0.1.0a2`. Earlier comparison observations belong to their original source commits.

## Install from the source archive

Download the `v0.1.0a2` **Source code** archive from the GitHub release, extract it, and run the following from the extracted directory with Python 3.11 or newer. Keep the extracted directory in place while using this editable installation.

```sh
python -m venv .venv
# Activate .venv for your shell.
python -m pip install -r requirements-lock.txt
python -m pip install --no-deps -e '.[dev]'
python -m pip check
spectral-audit --help
spectral-audit --version
```

The lock records a Windows CPython 3.11 environment. If a pinned wheel is unavailable on your platform, resolve compatible dependencies from `pyproject.toml` in this fresh environment and record that resolution. The installed distribution, imported package, and CLI should all report `0.1.0a2`. A standalone wheel is not supported because this preview uses its source-tree layout.

## Reproduce

From any working directory, use absolute paths to the extracted configurations and new output directories:

```sh
spectral-audit demo --config /path/to/extracted/configs/m0_tones.toml --out /path/to/new/demo
spectral-audit measure --config /path/to/extracted/configs/m1_welch_tones.toml --out /path/to/new/welch
spectral-audit measure --config /path/to/extracted/configs/m1_dwt_tones.toml --out /path/to/new/haar
spectral-audit boundary-audit --config /path/to/extracted/configs/m1_db4_boundaries.toml --out /path/to/new/db4
spectral-audit comparison-audit --config /path/to/extracted/configs/m1_comparison_controls.toml --out /path/to/new/comparison
```

Schema-v1 measures finite-record DFT mean-square band powers. Schema-v2 records DFT/Welch quantities and separate method totals; schema-v3 adds native Haar groups. The db4 audit compares two boundary modes. The comparison policy checks compatible targets separately from numerical agreement, accepts supported exact identities, permits an explicitly requested coefficient-mean-square to record-contribution normalization conversion, and permits descriptive DFT/Welch and db4 periodic/periodization differences. Its 38 fixed controls include injected numerical disagreement and an undefined ratio; their outcomes are evidence only for that suite. Archive runs without applicable Git metadata report `source_state=unversioned`, null `source_revision`, source-file hashes, and a source digest.

The archive contains `configs/`, `requirements-lock.txt`, `LICENSE`, `README.md`, and `docs/`. M1 remains partial. Offset controls, other extension modes, Welch variants, and broader comparison coverage are reserved for later work. M2–M4 and the planned `0.1.0` research release remain separate.
