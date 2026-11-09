"""Generate deterministic uncertainty and synthetic timing evidence."""

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from timing import comparison, drift, statistics
from uncertainty import Sampling, monte_carlo, propagate, rectangular, type_a


def uncertainty_report():
    components = [type_a("length_mm", [100.01, 100.00, 100.02, 99.99, 100.01]),
                  rectangular("zero_correction_mm", 0, .02),
                  rectangular("thermal_correction_mm", 0, .01)]
    def model(inputs):
        return inputs[0] + inputs[1] + inputs[2]
    return {"model": "length + zero correction + thermal correction, all in mm",
            "assumptions": "independent components; Type A normal approximation; Type B rectangular",
            "gum": propagate(model, components), "monte_carlo": monte_carlo(model, components, Sampling())}


def timing_report(destination):
    generator = np.random.default_rng(2026)
    clean = generator.normal(20, 50, 2000)
    impaired = generator.normal(100, 300, 2000)
    impaired[::100] += 3000
    np.savetxt(destination / "synthetic_offsets.csv", np.column_stack((clean, impaired)),
               delimiter=",", header="clean_ns,impaired_ns", comments="")
    figure, axis = plt.subplots(figsize=(8, 4))
    axis.hist(clean, bins=60, alpha=.6, label="synthetic baseline")
    axis.hist(impaired, bins=60, alpha=.6, label="synthetic delay spikes")
    axis.set(xlabel="Offset / ns", ylabel="Count", title="Synthetic timing distribution; no hardware measurements")
    axis.legend()
    figure.tight_layout()
    figure.savefig(destination / "timing_histogram.png", dpi=140)
    plt.close(figure)
    return {"provenance": "SYNTHETIC", "baseline": statistics(clean), "impaired": statistics(impaired),
            "comparison": comparison(impaired, clean),
            "known_drift": drift([i*1000000000 for i in range(20)], [10+1000*i for i in range(20)])}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    destination = parser.parse_args().output
    destination.mkdir(parents=True, exist_ok=True)
    report = {"uncertainty": uncertainty_report(), "timing": timing_report(destination)}
    (destination / "measurement_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
