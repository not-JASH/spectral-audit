"""Installed M0 command-line interface."""

import argparse
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from spectral_audit import __version__
from spectral_audit.boundary_audit import run as run_boundary_audit
from spectral_audit.comparison_audit import run as run_comparison_audit
from spectral_audit.config import load_demo_config, load_measure_config
from spectral_audit.estimators.dwt import measure_dwt
from spectral_audit.estimators.welch import measure_welch
from spectral_audit.io import write_demo_run, write_measure_run
from spectral_audit.reference import fourier_reference
from spectral_audit.signals import make_tones


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spectral-audit", description="Finite-record DFT, Welch, and bounded Haar DWT"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="run the deterministic two-tone demonstration")
    demo.add_argument("--config", required=True, type=Path, help="schema-v1 TOML configuration")
    demo.add_argument("--out", required=True, type=Path, help="new or empty output directory")
    measure = commands.add_parser("measure", help="run schema-v2 or v3 measurement")
    measure.add_argument(
        "--config", required=True, type=Path, help="schema-v2 or v3 TOML configuration"
    )
    measure.add_argument("--out", required=True, type=Path, help="new or empty output directory")
    boundary = commands.add_parser("boundary-audit", help="run bounded db4 boundary audit")
    boundary.add_argument("--config", required=True, type=Path)
    boundary.add_argument("--out", required=True, type=Path)
    comparison = commands.add_parser("comparison-audit", help="run bounded M1 comparison controls")
    comparison.add_argument("--config", required=True, type=Path)
    comparison.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    started = datetime.now(UTC)
    clock = time.perf_counter()
    try:
        if args.out.exists() and (not args.out.is_dir() or any(args.out.iterdir())):
            raise ValueError(f"output directory already exists and is nonempty: {args.out}")
        root = Path(__file__).resolve().parents[2]
        if args.command == "boundary-audit":
            manifest = run_boundary_audit(args.config, args.out, root)
            print(f"boundary audit: {len(manifest['input_records'])} input records")
            print(args.out / "manifest.json")
            return 0
        if args.command == "comparison-audit":
            manifest = run_comparison_audit(args.config, args.out, root)
            print(
                f"comparison audit: {len(manifest['resolved_configuration']['controls'])} controls"
            )
            print(args.out / "manifest.json")
            return 0
        if args.command == "demo":
            config = load_demo_config(args.config)
            record = make_tones(config.signal, config.record)
            measurement = fourier_reference(record, config.bands)
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
        else:
            config = load_measure_config(args.config)
            record = make_tones(config.tones.signal, config.tones.record)
            measurement = fourier_reference(record, config.tones.bands)
            estimate = measure_welch(record, config.tones.bands, config.welch)
            native = measure_dwt(record, config.dwt) if config.dwt is not None else None
            arguments = ["measure", "--config", str(args.config), "--out", "<output-directory>"]
            paths = write_measure_run(
                args.out,
                config,
                record,
                measurement,
                estimate,
                args.config,
                root,
                started,
                time.perf_counter() - clock,
                arguments,
                native,
            )
    except (ValueError, FileNotFoundError, PermissionError) as exc:
        print(f"spectral-audit: {exc}", file=sys.stderr)
        return 2
    except (OSError, RuntimeError) as exc:
        print(f"spectral-audit: {exc}", file=sys.stderr)
        return 1
    print(f"record mean-square power: {measurement.record_power:.12g} ({record.sample_unit})^2")
    if args.command == "measure":
        print(f"Welch method total: {estimate.method_total:.12g} ({record.sample_unit})^2")
    for band, power, fraction in zip(
        measurement.bands, measurement.powers, measurement.fractions, strict=True
    ):
        fraction_text = str(fraction) if fraction is not None else "undefined"
        print(f"{band.name}: {power:.12g}; record fraction: {fraction_text}")
    for path in (paths.csv, paths.native_scales, paths.summary, paths.manifest):
        if path is None:
            continue
        print(path)
    return 0
