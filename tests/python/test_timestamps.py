import pytest

from client.timestamp_check import check_timestamps


def test_regular_timestamps_have_no_timing_errors_or_constant_bits():
    report = check_timestamps(list(range(16)), nominal_period=1, bit_width=4)

    assert report.intervals == [1] * 15
    assert report.deviations == [0] * 15
    assert report.out_of_tolerance == []
    assert report.non_increasing == []
    assert report.constant_bits == {}


def test_tolerance_includes_both_boundaries_and_reports_signed_deviations():
    report = check_timestamps([0, 12, 20, 33], nominal_period=10, tolerance=2)

    assert report.deviations == [2, -2, 3]
    assert report.out_of_tolerance == [3]
    assert report.non_increasing == []


@pytest.mark.parametrize(
    ("timestamps", "expected_errors", "expected_non_increasing"),
    [
        ([0, 10, 30, 40], [2], []),
        ([0, 10, 10, 20], [2], [2]),
        ([0, 20, 10, 30], [1, 2, 3], [2]),
    ],
    ids=["missing-frame", "repeated-frame", "reordered-frames"],
)
def test_frame_anomalies_identify_the_later_frame(
    timestamps, expected_errors, expected_non_increasing
):
    report = check_timestamps(timestamps, nominal_period=10)

    assert report.out_of_tolerance == expected_errors
    assert report.non_increasing == expected_non_increasing


@pytest.mark.parametrize("forced_value", [0, 1], ids=["stuck-low", "stuck-high"])
def test_injected_stuck_bit_is_reported(forced_value):
    timestamps = [(t & ~(1 << 2)) | (forced_value << 2) for t in range(32)]

    report = check_timestamps(timestamps, nominal_period=1, bit_width=5)

    assert report.constant_bits == {2: forced_value}
    assert report.out_of_tolerance


def test_regular_aligned_timestamps_can_have_constant_bits_without_timing_errors():
    report = check_timestamps([0, 16, 32, 48], nominal_period=16, bit_width=6)

    assert report.constant_bits == {0: 0, 1: 0, 2: 0, 3: 0}
    assert report.out_of_tolerance == []
    assert report.non_increasing == []


def test_large_integer_timestamps_preserve_single_tick_differences():
    start = 2**60
    report = check_timestamps([start, start + 1, start + 2], nominal_period=1)

    assert report.intervals == [1, 1]
    assert report.out_of_tolerance == []


def test_counter_rollover_is_flagged_without_automatic_correction():
    report = check_timestamps([250, 255, 4], nominal_period=5, bit_width=8)

    assert report.intervals == [5, -251]
    assert report.out_of_tolerance == [2]
    assert report.non_increasing == [2]


@pytest.mark.parametrize(
    ("timestamps", "period", "tolerance", "bit_width"),
    [
        ([], 1, 0, 8),
        ([0], 1, 0, 8),
        ([0, 1], 0, 0, 8),
        ([0, 1], 1, -1, 8),
        ([0, 1], 1, 0, 0),
        ([0, 1], 1, 0, 65),
        ([-1, 0], 1, 0, 8),
        ([0, 256], 1, 0, 8),
        ([0, 1.5], 1, 0, 8),
    ],
)
def test_invalid_samples_or_parameters_are_rejected(timestamps, period, tolerance, bit_width):
    with pytest.raises(ValueError):
        check_timestamps(timestamps, period, tolerance, bit_width)
