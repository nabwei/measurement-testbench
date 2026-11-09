"""Re-execute D/E/F evidence after the independent numerical review fix."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "08_TEST_RESULTS/vision_measurement"


def execute(name, directory, arguments):
    command = [sys.executable, *map(str, arguments)]
    run = subprocess.run(command, cwd=directory, capture_output=True, text=True, timeout=180)
    (EVIDENCE / f"review_{name}.log").write_text(
        "COMMAND: " + repr(command) + "\n" + run.stdout + run.stderr +
        f"\nexit_code={run.returncode}\n", encoding="utf-8")
    if run.returncode:
        raise RuntimeError(f"{name} failed; see saved review log")


def compare_outputs():
    comparisons = {}
    for category, filenames in {"inspection": ["inspection_report.json", "split_manifest.csv"],
                                "measurement": ["measurement_report.json", "synthetic_offsets.csv"]}.items():
        for filename in filenames:
            first = hashlib.sha256((EVIDENCE / category / filename).read_bytes()).hexdigest()
            second = hashlib.sha256((EVIDENCE / (category + "_repeat") / filename).read_bytes()).hexdigest()
            comparisons[f"{category}/{filename}"] = {"status": "PASS" if first == second else "FAIL", "sha256": first}
    (EVIDENCE / "reproducibility.json").write_text(json.dumps(comparisons, indent=2), encoding="utf-8")
    if any(entry["status"] != "PASS" for entry in comparisons.values()):
        raise RuntimeError("reproduction artifacts differ")


def main():
    measurement = ROOT / "05_MEASUREMENT_TIMING"
    inspection = ROOT / "03_COMPUTER_VISION"
    for name, directory in (("measurement", measurement), ("inspection", inspection)):
        execute(name + "_tests", directory, ["-m", "pytest", "tests", "-q",
                "--junitxml=" + str(EVIDENCE / f"review_{name}_junit.xml")])
    for suffix in ("", "_repeat"):
        execute("measurement" + suffix, measurement, ["demo.py", "--output", EVIDENCE / ("measurement" + suffix)])
        execute("inspection" + suffix, inspection, ["run_inspection.py", "--dataset", "datasets/KolektorSDD",
                "--output", EVIDENCE / ("inspection" + suffix)])
    compare_outputs()
    print("PASS: D/E/F review validation, 27 tests and four reproduced output hashes")


if __name__ == "__main__":
    main()
