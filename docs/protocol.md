# Demonstration protocol

This protocol was defined for this standalone simulator. It is not compatible
with an institute or commercial device protocol.

The loopback harness sends one hexadecimal line per complete request and
receives one line per reply. This text envelope is a test transport; it does
not implement UART timing or recovery from a damaged byte stream.
An intentionally dropped response produces no line.

## Request: 6 bytes

| Offset | Size | Meaning |
| --- | --- | --- |
| 0 | 1 | Sync byte `0xD3` |
| 1 | 1 | Version `0x01` |
| 2 | 1 | Sequence number, 0 through 255 |
| 3 | 1 | Command `0x01`: read one synthetic sample |
| 4 | 2 | CRC over bytes 0 through 3, low byte first |

## Reply: 12 bytes

| Offset | Size | Meaning |
| --- | --- | --- |
| 0 | 1 | Sync byte `0xD3` |
| 1 | 1 | Version `0x01` |
| 2 | 1 | Sequence number |
| 3 | 1 | Status code |
| 4 | 4 | Unsigned timestamp in arbitrary ticks, little-endian |
| 8 | 2 | Unsigned synthetic sample value, little-endian |
| 10 | 2 | CRC over bytes 0 through 9, low byte first |

CRC parameters: width 16, polynomial `0x1021`, initial value `0xFFFF`,
no input/output reflection, final XOR `0x0000`. The ASCII check string
`123456789` yields `0x29B1`. The Python codec uses
[`binascii.crc_hqx`](https://docs.python.org/3.12/library/binascii.html#binascii.crc_hqx)
with initial value `0xFFFF`; the C++ implementation is an explicit bit loop.

## Request validation and errors

Checks run in this order; the first failed check determines the reply.

| Status | Meaning | Reply sequence |
| --- | --- | --- |
| 0 | Accepted read request | Request sequence |
| 1 | Wrong request length | `0xFF` |
| 2 | Wrong sync byte or unsupported version | `0xFF` |
| 3 | Invalid CRC | `0xFF` |
| 4 | Unknown command after successful header/CRC checks | Request sequence |

An error reply contains zero timestamp/value fields and a valid reply CRC.
The sequence in an invalid request is not trusted. `0xFF` can also be a normal
sequence number; always inspect the status field.
Non-hexadecimal input and text lines other than 12 characters are represented
as an empty request and receive status 1.

The Python client checks reply length, header, CRC and status before accepting
sample fields. A nonzero status becomes `ValueError`; the acquisition report
records the rejected reply and lists its unfulfilled requested sequence as missing.
Duplicate or unrequested reply sequence numbers are also rejected.

## Model and injected faults

For an accepted request with sequence `s`, the clean model returns:

```text
timestamp = 1000 * s
value = 1000 + 3 * s
```

The simulator is stateless. Repeating a request returns the same model value.
Faults are selected by its command-line mode:

- `jitter`: add 200 to the timestamp for sequence 5.
- `duplicate`: subtract 1000 from the timestamp for sequence 5.
- `missing`: suppress the reply for sequence 5.
- `corrupt`: flip bit 0 of byte 8 in reply 5 after its CRC is calculated.
- `stuck-low`: clear timestamp bit 7 for every sample before calculating CRC.

No hardware timing, serial-port behaviour, retransmission, physical sensor
accuracy, or adversarial security is modelled.
