#include "protocol.hpp"

#include <iomanip>
#include <iostream>
#include <map>
#include <string>

int main(int argc, char* argv[]) {
    const std::map<std::string, bench::Fault> modes{
        {"clean", bench::Fault::none}, {"jitter", bench::Fault::jitter},
        {"duplicate", bench::Fault::duplicate}, {"corrupt", bench::Fault::corrupt},
        {"missing", bench::Fault::missing}, {"stuck-low", bench::Fault::stuck_low},
    };
    if (argc != 2 || modes.count(argv[1]) == 0) {
        std::cerr << "Usage: sensor_sim clean|jitter|duplicate|corrupt|missing|stuck-low\n";
        return 2;
    }
    const auto nibble = [](char c) {
        if (c >= '0' && c <= '9') return c - '0';
        if (c >= 'a' && c <= 'f') return c - 'a' + 10;
        if (c >= 'A' && c <= 'F') return c - 'A' + 10;
        return -1;
    };
    std::string line;
    while (std::getline(std::cin, line)) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        bench::Bytes request;
        // Each line represents exactly one binary request in the loopback harness.
        if (line.size() == 12) {
            for (std::size_t index = 0; index < line.size(); index += 2) {
                const int high = nibble(line[index]), low = nibble(line[index + 1]);
                if (high < 0 || low < 0) {
                    request.clear();
                    break;
                }
                request.push_back(static_cast<std::uint8_t>((high << 4) | low));
            }
        }
        const auto response = bench::respond(request, modes.at(argv[1]));
        if (response.empty()) continue;
        for (const auto byte : response) {
            std::cout << std::hex << std::setfill('0') << std::setw(2)
                      << static_cast<unsigned>(byte);
        }
        std::cout << '\n';
    }
    return 0;
}
