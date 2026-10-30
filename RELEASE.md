# v0.1.0a1 source preview

Prepared 2026-10-30 from pre-comparison source commit `6a10c4e0c1b8f39e2fd36897451939ac8fd55fcf`. This preview's release preparation commit is the source identified by its `v0.1.0a1` tag. It has no comparison-audit command.

## Install from the source archive

Download the `v0.1.0a1` **Source code** archive from the GitHub release, extract it, and run the following from the extracted directory with Python 3.11 or newer. Keep the extracted directory in place while using this editable installation.

```sh
python -m venv .venv
# Activate .venv for your shell.
python -m pip install -r requirements-lock.txt
python -m pip install --no-deps -e '.[dev]'
python -m pip check
spectral-audit --help
spectral-audit --version
```

The lock records a Windows CPython 3.11 environment. If a pinned wheel is unavailable on your platform, resolve compatible dependencies from `pyproject.toml` in this fresh environment and record that resolution. The installed distribution, imported package, and CLI should all report `0.1.0a1`. A standalone wheel is not supported because this preview uses its source-tree layout.

## Reproduce

From any working directory, use absolute paths to the extracted configurations and new output directories:

```sh
spectral-audit demo --config /path/to/extracted/configs/m0_tones.toml --out /path/to/new/demo
spectral-audit measure --config /path/to/extracted/configs/m1_welch_tones.toml --out /path/to/new/welch
spectral-audit measure --config /path/to/extracted/configs/m1_dwt_tones.toml --out /path/to/new/haar
spectral-audit boundary-audit --config /path/to/extracted/configs/m1_db4_boundaries.toml --out /path/to/new/db4
```

The schema-v1 DFT demo measures finite-record mean-square band power. Schema-v2 reports DFT and explicitly configured Welch quantities with separate actual-record and method totals. Schema-v3 adds separately labeled native Haar groups. The db4 audit compares periodization and periodic boundary behavior at bounded lengths. The archive contains `configs/`, `requirements-lock.txt`, `LICENSE`, `README.md`, and `docs/`. Runs from an archive without applicable Git metadata report `source_state=unversioned` and a null `source_revision`; the manifest retains source-file hashes and digest.

These are finite deterministic checks, not general diagnostic performance evidence. M1 remains partial; offset controls, other extension modes, Welch variants, and broader comparison work remain open. M2–M4 and the planned `0.1.0` research release remain separate.
