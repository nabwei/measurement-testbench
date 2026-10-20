#pragma once

#include <cstdint>
#include <vector>

namespace bench {
using Bytes = std::vector<std::uint8_t>;
enum class Status : std::uint8_t { ok = 0, length = 1, header = 2, crc = 3, command = 4 };
enum class Fault { none, jitter, duplicate, corrupt, missing, stuck_low };

// CRC-16: polynomial 0x1021, initial 0xFFFF, no reflection, final XOR 0.
std::uint16_t crc16(const Bytes& data);

// Fixed synthetic sensor model; an empty reply means an injected missing frame.
Bytes respond(const Bytes& request, Fault fault = Fault::none);
}  // namespace bench
