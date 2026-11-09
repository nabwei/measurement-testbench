Public extension setup (run from the repository root):

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-extensions.txt
cd 05_MEASUREMENT_TIMING
../.venv/bin/python -m pytest tests -q
```

The optional notebook additionally needs Jupyter/ipykernel. Historical evidence paths below refer to locally generated outputs; see the [current portfolio validation summary](https://github.com/nabwei/engineering-portfolio/blob/main/docs/VALIDATION.md).
# Measurement uncertainty and timing analysis

Projects E (NEW) and F (EXTENSION to the scope of measurement-testbench; no copied protocol implementation).

Run from this directory using the portfolio Python environment:

```sh
../.venv/bin/python -m pytest tests -q
../.venv/bin/python demo.py --output ../08_TEST_RESULTS/vision_measurement/measurement
../.venv/bin/python linux_clock_probe.py --output ../08_TEST_RESULTS/vision_measurement/linux_clock.json
```

The last command requires Linux and reads CLOCK_MONOTONIC. It measures scheduler wake-up lateness, not PTP offset or hardware timestamp precision. No clock is adjusted.

Numerical differentiation scales each step by the larger of the absolute estimate and its standard uncertainty; it does not impose a one-unit floor that would distort nanometre or nanosecond inputs. An exactly zero estimate with zero uncertainty uses a unit fallback only for that zero-contribution coordinate. Non-smooth models, singularities and ill-conditioned scales still require analytic checks or Monte Carlo cross-checks; a finite difference is not a proof of local linearity.

The Linux collector uses only the Python standard library, so `python3 linux_clock_probe.py --output capture.json` also works before the scientific environment is installed. It preserves raw nanosecond samples and device names; use `timing.statistics(capture["samples_ns"])` in the analysis environment for summary statistics. A listed virtual PHC is not evidence of a physical NIC hardware-timestamp experiment.

For the first two commands on Windows use `../.venv-win/Scripts/python.exe`. Exact tested package versions are in `requirements-tested.txt`. `uncertainty_walkthrough.ipynb` contains a reproducible example; the executed copy and kernel log are saved in the evidence directory. Analyze an existing linuxptp log with `python analyze_ptp_log.py capture.log --provenance SOFTWARE_ONLY --output report.json`; provenance is user-supplied metadata and not inferred from log syntax.

`uncertainty.py` implements scalar first-order propagation `u_c² = J C Jᵀ`. `type_a` estimates uncertainty of a mean as sample standard deviation divided by sqrt(n); this assumes independent observations. `rectangular` converts a symmetric Type B half-width to standard uncertainty by sqrt(3). Type A/B describes evaluation, not an inherent probability distribution. The caller explicitly selects normal or uniform inputs. `propagate` uses a central finite difference gradient; inspect sensitivity to step size for stiff models. Expanded uncertainty is `k u_c`, with k=2 default, and does not guarantee exactly 95% coverage. No effective degrees of freedom or Student-t coverage correction is implemented. Monte Carlo returns its own central 95% interval. Correlated Monte Carlo is supported only for normal inputs; correlated non-normal components fail explicitly. These calculations do not establish ISO compliance or laboratory accreditation.

`timing.py` derives PTP offset `(t2-t1 - (t4-t3))/2` and mean path delay `(t2-t1 + (t4-t3))/2`. Inputs are integer nanoseconds; differences precede floating conversion to retain precision at epoch-scale timestamps. Equal forward/reverse delay is an assumption. Asymmetry biases offset by half the delay difference. No wraparound inference is performed. Existing unsigned counter and interval validation remains in measurement-testbench.

Statistics include sample standard deviation, RMS, percentiles and peak-to-peak. Linear drift is expressed in ppm. `comparison` reports a difference of means and standard error under independent samples; autocorrelated offsets invalidate that standard error. Synthetic examples use seed 2026 and are labeled SYNTHETIC. Real local scheduler samples are SOFTWARE_ONLY. Hardware PTP is unverified.

`parse_ptp4l` accepts the `master offset` records emitted by linuxptp. It raises ValueError when fewer than two records are found. `ptp_exchange([0, 10, 9, 20])` raises ValueError because the slave clock runs backwards. This is expected rejection, not an empty successful report.

References checked 2026-10-25: [BIPM JCGM 100:2008 and JCGM 101:2008](https://www.bipm.org/en/web/guest/publications/guides); [linuxptp ptp4l options](https://www.linuxptp.org/documentation/ptp4l/). Software timestamp mode is selected with `-S`; hardware operation additionally needs a PHC-capable device.

## Isolated actual software PTP capture

On Linux with linuxptp, iproute2 and the portfolio environment, explicitly run from the portfolio root:

```sh
sudo bash 05_MEASUREMENT_TIMING/run_ptp_namespace.sh /tmp/portfolio-ptp-fresh-output
```

The output directory must not already exist. This optional script creates two task-owned network namespaces and a veth pair, runs two real ptp4l processes for 30 seconds, and cleans up its processes and namespaces. A daemon that does not exit on TERM is killed after an additional five seconds. Unix sockets use a fresh, short temporary directory; cleanup unlinks only its four named sockets and removes that directory without recursive deletion. Both namespace removals are attempted even if one fails; the original failure status is preserved, and a cleanup-only failure also returns nonzero. Both configurations set `free_running 1`, so neither daemon adjusts the system clock. No physical interface or host routing is changed. Configurations, version, daemon logs and statistical report are retained. Missing privileges or daemon failures cause a nonzero exit.

Executed evidence is in `08_TEST_RESULTS/vision_measurement/ptp_veth`: 13 offset records, mean -177.54 ns, sample standard deviation 949.67 ns. These are one loaded-host capture, not guaranteed performance. Both endpoints share the host CLOCK_REALTIME; the result validates actual software-timestamp packet exchange and log analysis, not synchronization of independent oscillators. Physical timestamp and independent-clock experiments remain unverified. This privileged experiment is separate from the default aggregate runner.

After cleanup review, a separate actual capture in `ptp_veth_review` produced 13 records, mean 142.54 ns and sample standard deviation 559.27 ns. Post-checks confirmed removal of the task namespaces and socket directory. Synthetic command-stub fault tests separately verify both cleanup attempts and exit-status preservation; they are not PTP measurement data.
