"""Installed M0 command-line interface."""

import argparse
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from spectral_audit import __version__
from spectral_audit.config import load_demo_config
from spectral_audit.io import write_demo_run
from spectral_audit.reference import fourier_reference
from spectral_audit.signals import make_tones


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spectral-audit", description="M0 finite-record DFT demonstration"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="run the deterministic two-tone demonstration")
    demo.add_argument("--config", required=True, type=Path, help="schema-v1 TOML configuration")
    demo.add_argument("--out", required=True, type=Path, help="new or empty output directory")
    args = parser.parse_args(argv)
    started = datetime.now(UTC)
    clock = time.perf_counter()
    try:
        if args.out.exists() and (not args.out.is_dir() or any(args.out.iterdir())):
            raise ValueError(f"output directory already exists and is nonempty: {args.out}")
        config = load_demo_config(args.config)
        record = make_tones(config.signal, config.record)
        measurement = fourier_reference(record, config.bands)
        root = Path(__file__).resolve().parents[2]
        arguments = ["demo", "--config", str(args.config), "--out", "<output-directory>"]
        paths = write_demo_run(
            args.out,
            config,
            record,
            measurement,
            args.config,
            root,
            started,
            time.perf_counter() - clock,
            arguments,
        )
    except (ValueError, FileNotFoundError, PermissionError) as exc:
        print(f"spectral-audit: {exc}", file=sys.stderr)
        return 2
    except (OSError, RuntimeError) as exc:
        print(f"spectral-audit: {exc}", file=sys.stderr)
        return 1
    print(f"record mean-square power: {measurement.record_power:.12g} ({record.sample_unit})^2")
    for band, power, fraction in zip(
        measurement.bands, measurement.powers, measurement.fractions, strict=True
    ):
        fraction_text = str(fraction) if fraction is not None else "undefined"
        print(f"{band.name}: {power:.12g}; record fraction: {fraction_text}")
    for path in (paths.csv, paths.summary, paths.manifest):
        print(path)
    return 0
