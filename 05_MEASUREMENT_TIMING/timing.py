"""PTP four-timestamp estimates and descriptive timing statistics, in ns."""

import re

import numpy as np


def ptp_exchange(timestamps):
    """t1/t4 master, t2/t3 slave; assumes equal forward/reverse delay."""
    if len(timestamps) != 4 or any(type(t) is not int for t in timestamps):
        raise ValueError("four integer nanosecond timestamps are required")
    t1, t2, t3, t4 = timestamps
    if t3 < t2 or t4 < t1:
        raise ValueError("local timestamps must not run backwards")
    forward, reverse = t2 - t1, t4 - t3
    delay = (forward + reverse) / 2
    if delay < 0:
        raise ValueError("negative round-trip network delay")
    return {"offset_ns": (forward - reverse) / 2, "path_delay_ns": delay}


def statistics(samples):
    samples = np.asarray(samples, dtype=float)
    if samples.ndim != 1 or len(samples) < 2 or not np.isfinite(samples).all():
        raise ValueError("statistics require at least two finite samples")
    return {"count": len(samples), "mean_ns": float(samples.mean()),
            "std_ns": float(samples.std(ddof=1)), "rms_ns": float(np.sqrt(np.mean(samples**2))),
            "p50_ns": float(np.quantile(samples, .5)), "p95_ns": float(np.quantile(samples, .95)),
            "p99_ns": float(np.quantile(samples, .99)), "min_ns": float(samples.min()),
            "max_ns": float(samples.max()), "peak_to_peak_ns": float(np.ptp(samples))}


def drift(time_ns, offset_ns):
    if len(time_ns) != len(offset_ns) or len(time_ns) < 2:
        raise ValueError("two or more paired timestamps/offsets are required")
    elapsed = np.asarray([t - time_ns[0] for t in time_ns], dtype=float) * 1e-9
    offsets = np.asarray(offset_ns, dtype=float)
    if not np.isfinite(elapsed).all() or not np.isfinite(offsets).all() or np.any(np.diff(elapsed) <= 0):
        raise ValueError("time must increase strictly and all samples must be finite")
    slope, intercept = np.linalg.lstsq(np.column_stack((elapsed, np.ones(len(elapsed)))), offsets, rcond=None)[0]
    return {"drift_ppm": float(slope / 1000), "initial_offset_ns": float(intercept)}


def parse_ptp4l(text):
    offsets = [int(match) for match in re.findall(r"master offset\s+(-?\d+)", text)]
    if len(offsets) < 2:
        raise ValueError("log contains fewer than two master-offset records")
    return offsets


def comparison(first, second):
    left, right = statistics(first), statistics(second)
    return {"mean_difference_ns": left["mean_ns"] - right["mean_ns"],
            "standard_error_ns": float(np.sqrt(left["std_ns"]**2 / left["count"] + right["std_ns"]**2 / right["count"])),
            "assumption": "Independent samples; serial correlation invalidates this standard error."}
