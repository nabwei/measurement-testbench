#include "protocol.hpp"

#include <cstddef>

namespace bench {
std::uint16_t crc16(const Bytes& data) {
    std::uint16_t crc = 0xFFFF;
    for (const auto byte : data) {
        crc ^= static_cast<std::uint16_t>(byte) << 8;
        for (int bit = 0; bit < 8; ++bit) {
            crc = static_cast<std::uint16_t>(
                (crc & 0x8000) ? (crc << 1) ^ 0x1021 : crc << 1);
        }
    }
    return crc;
}

static Bytes reply(std::uint8_t sequence, Status status,
                   std::uint32_t timestamp = 0, std::uint16_t value = 0) {
    Bytes bytes{0xD3, 1, sequence, static_cast<std::uint8_t>(status)};
    for (int shift = 0; shift < 32; shift += 8) {
        bytes.push_back(static_cast<std::uint8_t>(timestamp >> shift));
    }
    bytes.push_back(static_cast<std::uint8_t>(value));
    bytes.push_back(static_cast<std::uint8_t>(value >> 8));
    const auto crc = crc16(bytes);
    bytes.push_back(static_cast<std::uint8_t>(crc));
    bytes.push_back(static_cast<std::uint8_t>(crc >> 8));
    return bytes;
}

Bytes respond(const Bytes& request, Fault fault) {
    if (request.size() != 6) return reply(0xFF, Status::length);
    if (request[0] != 0xD3 || request[1] != 1) return reply(0xFF, Status::header);
    const auto received_crc = request[4] | (request[5] << 8);
    if (crc16(Bytes(request.begin(), request.begin() + 4)) != received_crc) {
        return reply(0xFF, Status::crc);
    }
    const auto sequence = request[2];
    if (request[3] != 1) return reply(sequence, Status::command);

    // Arbitrary model in ticks and raw units, unrelated to any real instrument.
    std::uint32_t timestamp = static_cast<std::uint32_t>(sequence) * 1000;
    const auto value = static_cast<std::uint16_t>(1000 + 3 * sequence);
    if (sequence == 5) {
        if (fault == Fault::missing) return {};
        if (fault == Fault::jitter) timestamp += 200;
        if (fault == Fault::duplicate) timestamp -= 1000;
    }
    if (fault == Fault::stuck_low) timestamp &= ~(std::uint32_t{1} << 7);
    auto result = reply(sequence, Status::ok, timestamp, value);
    if (fault == Fault::corrupt && sequence == 5) result[8] ^= 1;
    return result;
}
}  // namespace bench
