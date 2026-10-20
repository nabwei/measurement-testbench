#include "protocol.hpp"
#include <gtest/gtest.h>

using bench::Bytes;

static Bytes request(std::uint8_t sequence, std::uint8_t command = 1) {
    Bytes frame{0xD3, 1, sequence, command};
    const auto crc = bench::crc16(frame);
    frame.push_back(static_cast<std::uint8_t>(crc));
    frame.push_back(static_cast<std::uint8_t>(crc >> 8));
    return frame;
}

TEST(Crc, StandardCheckValue) {
    const Bytes text{'1', '2', '3', '4', '5', '6', '7', '8', '9'};
    EXPECT_EQ(bench::crc16(text), 0x29B1);
}

TEST(Protocol, ReadReturnsSequenceTimestampAndValue) {
    const auto frame = bench::respond(request(7));
    ASSERT_EQ(frame.size(), 12u);
    const Bytes expected_body{0xD3, 1, 7, 0, 0x58, 0x1B, 0, 0, 0xFD, 3};
    EXPECT_EQ(Bytes(frame.begin(), frame.end() - 2), expected_body);
    EXPECT_EQ(frame[10] | (frame[11] << 8), bench::crc16(expected_body));
}

struct ErrorCase {
    const char* name;
    Bytes request;
    bench::Status status;
    std::uint8_t sequence;
};
class InvalidRequest : public ::testing::TestWithParam<ErrorCase> {};

TEST_P(InvalidRequest, ReturnsDefinedErrorWithValidReplyCrc) {
    const auto& example = GetParam();
    const auto frame = bench::respond(example.request);
    ASSERT_EQ(frame.size(), 12u);
    EXPECT_EQ(frame[2], example.sequence);
    EXPECT_EQ(frame[3], static_cast<std::uint8_t>(example.status));
    EXPECT_EQ(Bytes(frame.begin() + 4, frame.begin() + 10), Bytes(6, 0));
    EXPECT_EQ(frame[10] | (frame[11] << 8),
              bench::crc16(Bytes(frame.begin(), frame.end() - 2)));
}

INSTANTIATE_TEST_SUITE_P(
    RejectedFrames, InvalidRequest,
    ::testing::Values(
        ErrorCase{"Empty", {}, bench::Status::length, 0xFF},
        ErrorCase{"Truncated", {0xD3, 1, 7}, bench::Status::length, 0xFF},
        ErrorCase{"Sync", {0, 1, 7, 1, 0, 0}, bench::Status::header, 0xFF},
        ErrorCase{"Version", {0xD3, 2, 7, 1, 0, 0}, bench::Status::header, 0xFF},
        ErrorCase{"Crc", {0xD3, 1, 7, 1, 0, 0}, bench::Status::crc, 0xFF},
        ErrorCase{"Command", request(7, 99), bench::Status::command, 7}
    ),
    [](const ::testing::TestParamInfo<ErrorCase>& info) { return info.param.name; }
);
