"""Analyze existing ptp4l logs without configuring or adjusting clocks."""

import argparse
import json
from pathlib import Path

from timing import parse_ptp4l, statistics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=Path)
    parser.add_argument("--provenance", choices=["SYNTHETIC", "SOFTWARE_ONLY", "HARDWARE_TIMESTAMP"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    offsets = parse_ptp4l(arguments.log.read_text(encoding="utf-8"))
    report = {"provenance_user_asserted": arguments.provenance,
              "provenance_warning": "Log syntax does not verify timestamp hardware; retain acquisition evidence separately.",
              "offset_statistics": statistics(offsets)}
    arguments.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
