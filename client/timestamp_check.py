"""Check integer frame timestamps; all times use the same tick unit."""

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass
class Report:
    intervals: list[int]
    deviations: list[int]
    out_of_tolerance: list[int]
    non_increasing: list[int]
    constant_bits: dict[int, int]


def check_timestamps(
    timestamps: Sequence[int],
    nominal_period: int,
    tolerance: int = 0,
    bit_width: int = 64,
) -> Report:
    """Return interval errors and constant-bit candidates.

    Flagged indices refer to the later frame, counted from zero.
    Constant bits are observations, not proof of a hardware fault.
    Invalid parameters or unsigned timestamps raise ValueError.
    """
    if any(type(value) is not int for value in (nominal_period, tolerance, bit_width)):
        raise ValueError("period, tolerance and bit_width must be integers")
    if nominal_period <= 0 or tolerance < 0 or not 1 <= bit_width <= 64:
        raise ValueError("require period > 0, tolerance >= 0 and bit_width in 1..64")
    if len(timestamps) < 2:
        raise ValueError("at least two timestamps are required")
    if any(type(t) is not int or not 0 <= t < (1 << bit_width) for t in timestamps):
        raise ValueError("timestamps must be unsigned integers within bit_width")

    intervals = [current - previous for previous, current in zip(timestamps, timestamps[1:])]
    deviations = [interval - nominal_period for interval in intervals]
    out_of_tolerance = [
        index for index, error in enumerate(deviations, start=1) if abs(error) > tolerance
    ]
    non_increasing = [
        index for index, interval in enumerate(intervals, start=1) if interval <= 0
    ]

    constant_bits = {}
    for bit in range(bit_width):
        first_value = (timestamps[0] >> bit) & 1
        if all(((t >> bit) & 1) == first_value for t in timestamps):
            constant_bits[bit] = first_value

    return Report(intervals, deviations, out_of_tolerance, non_increasing, constant_bits)
