#include <chrono>
#include <iomanip>
#include <iostream>
#include <string>
#include <thread>

using Clock = std::chrono::steady_clock;

int main(int argc, char** argv) {
    const int samples = argc > 1 ? std::stoi(argv[1]) : 10;
    const int interval_ms = argc > 2 ? std::stoi(argv[2]) : 1000;

    std::cout << "sample,send_timestamp_ms,receive_timestamp_ms,latency_ms" << std::endl;

    for (int i = 0; i < samples; ++i) {
        const auto send_time = Clock::now();

        // Placeholder for real capture-side and playback-side timestamp matching.
        std::this_thread::sleep_for(std::chrono::milliseconds(35));

        const auto receive_time = Clock::now();
        const auto send_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                                 send_time.time_since_epoch())
                                 .count();
        const auto receive_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                                    receive_time.time_since_epoch())
                                    .count();
        const auto latency_ms = receive_ms - send_ms;

        std::cout << i << "," << send_ms << "," << receive_ms << "," << latency_ms
                  << std::endl;

        std::this_thread::sleep_for(std::chrono::milliseconds(interval_ms));
    }

    return 0;
}
