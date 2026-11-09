"""Measure local scheduler wake-up lateness; never changes any system clock."""

import argparse
import json
import platform
import time
from pathlib import Path

def wakeup_lateness(count, period_ns):
    if count < 2 or period_ns <= 0:
        raise ValueError("count >= 2 and positive period required")
    deadline = time.clock_gettime_ns(time.CLOCK_MONOTONIC)
    lateness = []
    for _ in range(count):
        deadline += period_ns
        remaining = deadline - time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        if remaining > 0:
            time.sleep(remaining / 1e9)
        lateness.append(time.clock_gettime_ns(time.CLOCK_MONOTONIC) - deadline)
    return lateness


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if platform.system() != "Linux":
        raise SystemExit("This probe requires Linux CLOCK_MONOTONIC")
    samples = wakeup_lateness(200, 1000000)
    report = {"provenance": "SOFTWARE_ONLY", "measurement": "local wake-up lateness, not PTP synchronization",
              "platform": platform.platform(), "sample_count": len(samples), "samples_ns": samples,
              "phc_devices": [str(path) for path in Path("/dev").glob("ptp*")]}
    arguments.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"SOFTWARE_ONLY: recorded {len(samples)} scheduler wake-up samples; PHCs: {report['phc_devices']}")


if __name__ == "__main__":
    main()
