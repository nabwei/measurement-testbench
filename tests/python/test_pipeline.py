import binascii
import csv
import json
import os
import subprocess
import struct
import sys
from pathlib import Path

import pytest

from client.protocol import parse_reply, request
from client.run import acquire

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def simulator():
    path = ROOT / "build" / "bin" / ("sensor_sim.exe" if os.name == "nt" else "sensor_sim")
    if not path.is_file():
        pytest.fail("Build sensor_sim with CMake before running pytest.")
    return path


def test_clean_loopback_preserves_all_synthetic_measurements(simulator):
    samples, report = acquire(simulator, "clean")

    assert [(s.sequence, s.timestamp, s.value) for s in samples] == [
        (index, 1000 * index, 1000 + 3 * index) for index in range(16)
    ]
    assert report["timing_and_transport_pass"] is True
    assert report["missing_sequences"] == []
    assert report["transport_errors"] == []


@pytest.mark.parametrize(
    ("scenario", "missing", "bad_timing", "non_increasing", "crc_errors"),
    [
        ("jitter", [], [5, 6], [], 0),
        ("duplicate", [], [5, 6], [5], 0),
        ("missing", [5], [5], [], 0),
        ("corrupt", [5], [5], [], 1),
    ],
)
def test_fault_injection_is_reported_across_both_languages(
    simulator, scenario, missing, bad_timing, non_increasing, crc_errors
):
    _, report = acquire(simulator, scenario)

    assert report["timing_and_transport_pass"] is False
    assert report["missing_sequences"] == missing
    assert report["timing"]["out_of_tolerance"] == bad_timing
    assert report["timing"]["non_increasing"] == non_increasing
    assert len(report["transport_errors"]) == crc_errors
    if crc_errors:
        assert report["transport_errors"][0]["error"] == "reply CRC mismatch"


def test_forced_low_timestamp_bit_is_a_candidate_in_the_final_report(simulator):
    _, clean = acquire(simulator, "clean")
    _, injected = acquire(simulator, "stuck-low")

    assert 7 not in clean["timing"]["constant_bits"]
    assert injected["timing"]["constant_bits"][7] == 0
    assert injected["timing"]["out_of_tolerance"]
    assert injected["timing_and_transport_pass"] is False


def test_device_rejects_bad_request_crc_and_unknown_command(simulator):
    corrupt = bytearray(request(2))
    corrupt[-1] ^= 1
    process = subprocess.run(
        [str(simulator), "clean"],
        input=corrupt.hex() + "\n" + request(3, command=99).hex() + "\n",
        text=True, capture_output=True, check=True, timeout=10,
    )
    frames = [bytes.fromhex(line) for line in process.stdout.splitlines()]

    assert [frame[3] for frame in frames] == [3, 4]
    assert [frame[2] for frame in frames] == [255, 3]
    for frame in frames:
        assert int.from_bytes(frame[-2:], "little") == binascii.crc_hqx(frame[:-2], 0xFFFF)


@pytest.mark.parametrize(("scenario", "expected_exit", "valid_count"), [
    ("clean", 0, 16), ("corrupt", 1, 15),
])
def test_cli_saves_machine_readable_results_and_returns_quality_status(
    simulator, tmp_path, scenario, expected_exit, valid_count
):
    process = subprocess.run(
        [sys.executable, "-m", "client.run", "--simulator", str(simulator),
         "--scenario", scenario, "--output", str(tmp_path)],
        cwd=ROOT, text=True, capture_output=True, timeout=15,
    )
    assert process.returncode == expected_exit, process.stderr
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    with (tmp_path / "samples.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == report["valid_samples"] == valid_count
    assert [int(row["sequence"]) for row in rows] == report["accepted_sequences"]
    assert report["timing_and_transport_pass"] is (expected_exit == 0)


def test_python_rejects_bad_reply_length():
    with pytest.raises(ValueError, match="length"):
        parse_reply(b"")


def encoded_reply(sequence, *, sync=0xD3, version=1, status=0):
    body = struct.pack("<BBBBIH", sync, version, sequence, status, 1000 * sequence, 1000)
    return body + binascii.crc_hqx(body, 0xFFFF).to_bytes(2, "little")


@pytest.mark.parametrize(("fields", "error"), [
    ({"status": 4}, "device status 4"),
    ({"sync": 0xD2}, "invalid reply header"),
    ({"version": 2}, "invalid reply header"),
])
def test_semantically_invalid_reply_is_rejected_even_with_valid_crc(fields, error):
    with pytest.raises(ValueError, match=error):
        parse_reply(encoded_reply(2, **fields))


@pytest.mark.parametrize("extra_sequence", [3, 8], ids=["duplicate", "foreign"])
def test_extra_sequence_is_reported_and_not_accepted(monkeypatch, tmp_path, extra_sequence):
    frames = [encoded_reply(sequence).hex() for sequence in range(8)]
    frames.append(encoded_reply(extra_sequence).hex())
    process = subprocess.CompletedProcess([], 0, stdout="\n".join(frames), stderr="")
    monkeypatch.setattr(subprocess, "run", lambda *arguments, **options: process)

    samples, report = acquire(tmp_path / "synthetic-counterpart", "clean", count=8)

    assert [sample.sequence for sample in samples] == list(range(8))
    assert report["valid_samples"] == 8
    assert report["missing_sequences"] == []
    assert report["transport_errors"] == [
        {"reply_line": 9, "error": "unexpected or duplicate sequence"}
    ]
    assert report["timing_and_transport_pass"] is False


def test_unavailable_simulator_returns_execution_error_without_report(tmp_path):
    output = tmp_path / "results"
    process = subprocess.run(
        [sys.executable, "-m", "client.run", "--simulator", str(tmp_path / "missing"),
         "--output", str(output)],
        cwd=ROOT, text=True, capture_output=True, timeout=15,
    )
    assert process.returncode == 2
    assert not (output / "report.json").exists()
