"""Independent Python codec for the documented demonstration protocol."""

import binascii
import struct
from dataclasses import dataclass


@dataclass
class Sample:
    sequence: int
    timestamp: int
    value: int


def request(sequence: int, command: int = 1) -> bytes:
    body = bytes([0xD3, 1, sequence, command])
    return body + binascii.crc_hqx(body, 0xFFFF).to_bytes(2, "little")


def parse_reply(frame: bytes) -> Sample:
    if len(frame) != 12:
        raise ValueError("invalid reply length")
    if frame[:2] != bytes([0xD3, 1]):
        raise ValueError("invalid reply header")
    expected_crc = binascii.crc_hqx(frame[:-2], 0xFFFF)
    if int.from_bytes(frame[-2:], "little") != expected_crc:
        raise ValueError("reply CRC mismatch")
    sequence, status, timestamp, value = struct.unpack("<BBIH", frame[2:10])
    if status:
        raise ValueError(f"device status {status}")
    return Sample(sequence, timestamp, value)
