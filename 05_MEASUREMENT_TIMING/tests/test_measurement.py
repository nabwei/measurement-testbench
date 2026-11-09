import math

import pytest

from uncertainty import Component, Sampling, covariance, monte_carlo, propagate, rectangular, type_a
from timing import comparison, drift, parse_ptp4l, ptp_exchange, statistics


def test_mean_uncertainty_uses_sample_variance_and_sample_count():
    component = type_a("length", [1, 2, 3])
    assert component.estimate == 2
    assert component.standard_uncertainty == pytest.approx(1 / math.sqrt(3))


def test_correlated_linear_model_matches_closed_form_and_monte_carlo():
    components = [Component("x", 3, .2, "A", "normal"), Component("y", 4, .3, "B", "normal")]
    correlation = [[1, -.5], [-.5, 1]]
    propagated = propagate(lambda x: 2*x[0] + 3*x[1], components, correlation)
    expected = math.sqrt(.16 + .81 - .36)
    assert propagated["standard_uncertainty"] == pytest.approx(expected, rel=1e-8)
    simulated = monte_carlo(lambda x: 2*x[0] + 3*x[1], components, Sampling(80000, 7, correlation))
    assert simulated["standard_uncertainty"] == pytest.approx(expected, rel=.015)


def test_rectangular_bound_is_not_mistaken_for_standard_uncertainty():
    component = rectangular("resolution", 0, 3)
    estimated = monte_carlo(lambda x: x[0], [component], Sampling(80000, 12))
    assert estimated["standard_uncertainty"] == pytest.approx(math.sqrt(3), rel=.015)
    assert estimated["central_95_interval"] == pytest.approx([-2.85, 2.85], abs=.03)


@pytest.mark.parametrize("correlation", [[[1, 2], [2, 1]], [[1, 0], [.1, 1]], [[2, 0], [0, 1]]])
def test_invalid_correlation_cannot_generate_plausible_uncertainty(correlation):
    with pytest.raises(ValueError):
        covariance([rectangular("a", 1, 1), rectangular("b", 2, 1)], correlation)


def test_nonlinearity_is_visible_in_monte_carlo():
    components = [Component("x", 0, 1, "A", "normal")]
    assert propagate(lambda x: x[0]**2, components)["standard_uncertainty"] == 0
    simulated = monte_carlo(lambda x: x[0]**2, components, Sampling(100000, 30))
    assert simulated["mean"] == pytest.approx(1, abs=.02)
    assert simulated["standard_uncertainty"] == pytest.approx(math.sqrt(2), rel=.03)


@pytest.mark.parametrize("scale", [1e-9, 1.0, 1e9])
def test_sensitivity_preserves_physics_when_input_units_change(scale):
    component = Component("length", scale, .01*scale, "B", "normal")
    estimated = propagate(lambda x: scale/x[0], [component])
    assert estimated["sensitivity"]["length"] == pytest.approx(-1/scale, rel=1e-8)
    assert estimated["standard_uncertainty"] == pytest.approx(.01, rel=1e-8)


def test_zero_estimate_uses_uncertainty_scale_for_differentiation():
    component = Component("offset", 0, 1e-11, "B", "normal")
    estimated = propagate(lambda x: math.exp(x[0]/1e-9), [component])
    assert estimated["standard_uncertainty"] == pytest.approx(.01, rel=1e-8)


def test_ptp_large_epoch_keeps_nanosecond_differences():
    epoch = 1700000000000000000
    estimate = ptp_exchange([epoch, epoch + 130, epoch + 180, epoch + 250])
    assert estimate == {"offset_ns": 30, "path_delay_ns": 100}


def test_asymmetric_path_bias_is_half_delay_difference():
    # True offset 30; forward/reverse delays 120/80 imply an observed offset 50.
    assert ptp_exchange([0, 150, 200, 250])["offset_ns"] == 50


def test_drift_is_in_ppm_not_nanoseconds_per_second():
    epoch = 1700000000000000000
    estimated = drift([epoch + i*1000000000 for i in range(10)], [40+2000*i for i in range(10)])
    assert estimated["drift_ppm"] == pytest.approx(2)
    assert estimated["initial_offset_ns"] == pytest.approx(40)


def test_statistics_and_log_parser_preserve_negative_offsets():
    offsets = parse_ptp4l("ptp4l[1]: master offset -10 s2 freq +4 path delay 5\nptp4l[2]: master offset 10 s2 freq +3 path delay 6")
    assert statistics(offsets)["std_ns"] == pytest.approx(math.sqrt(200))
    assert comparison(offsets, [0, 20])["mean_difference_ns"] == -10


@pytest.mark.parametrize("timestamps", [[0, 10, 9, 20], [10, 0, 100, 20], [0, 1, 2], [0., 1, 2, 3]])
def test_invalid_exchange_is_rejected(timestamps):
    with pytest.raises(ValueError):
        ptp_exchange(timestamps)
