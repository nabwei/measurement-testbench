# Existing-code audit — 2026-10-25

Read through the authenticated GitHub connector before implementation:

| Repository/ref | Actual source inspected | Finding | Decision |
|---|---|---|---|
| measurement-testbench `7816da496de5072672922720348a0aee3082b1e2` | `client/timestamp_check.py`, `src/simulator.cpp` | Integer interval deviations, nonincreasing timestamps, constant bits, protocol fault modes already exist | EXISTING: retain these functions in their repository. F is an EXTENSION for four-timestamp PTP offset/delay, drift/statistics and Linux clock measurements; no replacement protocol simulator |
| phase-shift-demo `1259306a967ef3d72181ee972de6bbcf1ed22c9a` | `phase_demo/core.py` | Fringe synthesis, demodulation and row/column unwrapping already exist | EXISTING: do not recreate phase reconstruction |
| Excluded private research | Details retained only in the local, non-published source audit | Related geometry functionality already exists | EXISTING: no private code or data copied; public implementation remains separate |

E is NEW: covariance-aware uncertainty propagation and distribution cross-checks are not present in the inspected sources. D is NEW: industrial defect inspection is separate from existing structured-light geometry. This audit covers these listed source files, not an assertion that every historical commit was reviewed.
