"""Run the C++ counterpart, validate its synthetic measurements and save reports."""

import argparse
import csv
import json
import subprocess
from dataclasses import asdict
from pathlib import Path

from .protocol import Sample, parse_reply, request
from .timestamp_check import check_timestamps

SCENARIOS = ("clean", "jitter", "duplicate", "corrupt", "missing", "stuck-low")


def acquire(simulator: Path, scenario: str, count: int = 16) -> tuple[list[Sample], dict]:
    if scenario not in SCENARIOS or not 8 <= count <= 256:
        raise ValueError("choose a known scenario and a sample count in 8..256")
    requests = "".join(request(sequence).hex() + "\n" for sequence in range(count))
    process = subprocess.run(
        [str(simulator.resolve()), scenario],
        input=requests, text=True, capture_output=True, check=True, timeout=10,
    )
    samples, errors, seen = [], [], set()
    for line_number, line in enumerate(process.stdout.splitlines(), start=1):
        try:
            sample = parse_reply(bytes.fromhex(line))
            if sample.sequence >= count or sample.sequence in seen:
                raise ValueError("unexpected or duplicate sequence")
        except ValueError as error:
            errors.append({"reply_line": line_number, "error": str(error)})
            continue
        seen.add(sample.sequence)
        samples.append(sample)
    timing = None
    if len(samples) >= 2:
        timing = asdict(check_timestamps(
            [sample.timestamp for sample in samples],
            nominal_period=1000, tolerance=50, bit_width=32,
        ))
    missing = sorted(set(range(count)) - seen)
    passed = (
        not errors and not missing and timing is not None
        and not timing["out_of_tolerance"] and not timing["non_increasing"]
    )
    report = {
        "scenario": scenario,
        "synthetic": True,
        "timestamp_unit": "tick",
        "nominal_period": 1000,
        "tolerance": 50,
        "requested_samples": count,
        "valid_samples": len(samples),
        "missing_sequences": missing,
        "transport_errors": errors,
        "accepted_sequences": [sample.sequence for sample in samples],
        "timing": timing,
        "timing_and_transport_pass": passed,
        "note": "Constant bits are candidates, not proof of a hardware fault.",
    }
    return samples, report


def save_report(directory: Path, samples: list[Sample], report: dict) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "samples.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["sequence", "timestamp_ticks", "value_raw"])
        writer.writerows((sample.sequence, sample.timestamp, sample.value) for sample in samples)
    (directory / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulator", required=True, type=Path)
    parser.add_argument("--scenario", choices=SCENARIOS, default="clean")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        samples, report = acquire(args.simulator, args.scenario)
        save_report(args.output, samples, report)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(2, f"error: {error}\n")
    print(json.dumps({
        "scenario": report["scenario"],
        "valid_samples": report["valid_samples"],
        "timing_and_transport_pass": report["timing_and_transport_pass"],
        "output": str(args.output),
    }, indent=2))
    return 0 if report["timing_and_transport_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
