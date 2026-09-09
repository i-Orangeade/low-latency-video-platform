#include <algorithm>
#include <cerrno>
#include <chrono>
#include <cmath>
#include <csignal>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <poll.h>
#include <sstream>
#include <stdexcept>
#include <string>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include <vector>

namespace {

struct Options {
    std::string url;
    std::string sidecar;
    std::string timestamps_file;
    std::string output{"-"};
    std::size_t max_frames{250};
    int timeout_seconds{30};
};

struct Sample {
    std::size_t index;
    double pts_seconds;
    std::int64_t capture_ns;
    std::int64_t receive_ns;
    double latency_ms;
};

std::int64_t realtime_ns() {
    return std::chrono::duration_cast<std::chrono::nanoseconds>(
               std::chrono::system_clock::now().time_since_epoch())
        .count();
}

void usage(std::ostream& out) {
    out << "Usage:\n"
        << "  latency_probe --url URL --sidecar FILE [--output FILE]"
           " [--max-frames N] [--timeout SEC]\n"
        << "  latency_probe --timestamps-file FILE --sidecar FILE [--output FILE]\n\n"
        << "The URL is passed directly to ffmpeg via execvp (never through a shell).\n"
        << "Offline rows are: pts_seconds,receive_epoch_ns (receive time is optional).\n";
}

std::size_t parse_size(const std::string& value, const char* name) {
    std::size_t consumed = 0;
    const auto parsed = std::stoull(value, &consumed);
    if (consumed != value.size() || parsed == 0) {
        throw std::runtime_error(std::string(name) + " must be a positive integer");
    }
    return static_cast<std::size_t>(parsed);
}

Options parse_options(int argc, char** argv) {
    Options options;
    for (int i = 1; i < argc; ++i) {
        const std::string arg(argv[i]);
        if (arg == "--help" || arg == "-h") {
            usage(std::cout);
            std::exit(0);
        }
        if (i + 1 >= argc) {
            throw std::runtime_error("missing value for " + arg);
        }
        const std::string value(argv[++i]);
        if (arg == "--url") {
            options.url = value;
        } else if (arg == "--sidecar") {
            options.sidecar = value;
        } else if (arg == "--timestamps-file") {
            options.timestamps_file = value;
        } else if (arg == "--output") {
            options.output = value;
        } else if (arg == "--max-frames") {
            options.max_frames = parse_size(value, "--max-frames");
        } else if (arg == "--timeout") {
            options.timeout_seconds = static_cast<int>(parse_size(value, "--timeout"));
        } else {
            throw std::runtime_error("unknown option: " + arg);
        }
    }
    if (options.sidecar.empty()) {
        throw std::runtime_error("--sidecar is required");
    }
    if (options.url.empty() == options.timestamps_file.empty()) {
        throw std::runtime_error("provide exactly one of --url or --timestamps-file");
    }
    if (!options.url.empty() && options.url.front() == '-') {
        throw std::runtime_error("URL must not start with '-'");
    }
    return options;
}

std::map<std::string, std::string> read_sidecar(const std::string& path) {
    std::ifstream input(path);
    if (!input) {
        throw std::runtime_error("cannot open sidecar: " + path);
    }
    std::map<std::string, std::string> values;
    std::string line;
    while (std::getline(input, line)) {
        if (line.empty() || line[0] == '#') {
            continue;
        }
        const auto equals = line.find('=');
        if (equals == std::string::npos) {
            throw std::runtime_error("invalid sidecar line: " + line);
        }
        values[line.substr(0, equals)] = line.substr(equals + 1);
    }
    return values;
}

template <typename T>
T parse_number(const std::string& text, const char* description) {
    std::istringstream stream(text);
    T value{};
    stream >> value;
    if (!stream || stream.peek() != std::char_traits<char>::eof()) {
        throw std::runtime_error(std::string("invalid ") + description + ": " + text);
    }
    return value;
}

double parse_pts_line(const std::string& line) {
    const auto comma = line.find(',');
    const std::string first = line.substr(0, comma);
    if (first.empty() || first == "N/A") {
        throw std::runtime_error("frame has no usable timestamp");
    }
    return parse_number<double>(first, "frame PTS");
}

double parse_showinfo_pts(const std::string& line) {
    if (line.find("showinfo") == std::string::npos) {
        throw std::runtime_error("not a showinfo frame");
    }
    const std::string marker = "pts_time:";
    const auto marker_position = line.find(marker);
    if (marker_position == std::string::npos) {
        throw std::runtime_error("showinfo frame has no PTS");
    }
    const auto value_start = line.find_first_not_of(" \t", marker_position + marker.size());
    if (value_start == std::string::npos) {
        throw std::runtime_error("showinfo frame has empty PTS");
    }
    const auto value_end = line.find_first_of(" \t\r\n", value_start);
    return parse_number<double>(line.substr(value_start, value_end - value_start),
                                "frame PTS");
}

Sample make_sample(std::size_t index, double pts, std::int64_t receive_ns,
                   std::int64_t source_start_ns, double pts_origin) {
    const auto offset_ns = static_cast<std::int64_t>(
        std::llround((pts - pts_origin) * 1000000000.0));
    const std::int64_t capture_ns = source_start_ns + offset_ns;
    return {index, pts, capture_ns, receive_ns,
            static_cast<double>(receive_ns - capture_ns) / 1000000.0};
}

std::vector<Sample> read_offline(const Options& options, std::int64_t source_start_ns,
                                 double pts_origin) {
    std::ifstream input(options.timestamps_file);
    if (!input) {
        throw std::runtime_error("cannot open timestamps file: " + options.timestamps_file);
    }
    std::vector<Sample> samples;
    std::string line;
    while (samples.size() < options.max_frames && std::getline(input, line)) {
        if (line.empty() || line[0] == '#') {
            continue;
        }
        const auto comma = line.find(',');
        const double pts = parse_pts_line(line);
        const std::int64_t receive_ns =
            comma == std::string::npos
                ? realtime_ns()
                : parse_number<std::int64_t>(line.substr(comma + 1), "receive timestamp");
        samples.push_back(
            make_sample(samples.size(), pts, receive_ns, source_start_ns, pts_origin));
    }
    return samples;
}

std::vector<Sample> probe_live(const Options& options, std::int64_t source_start_ns,
                               double pts_origin) {
    int pipe_fds[2];
    if (pipe(pipe_fds) != 0) {
        throw std::runtime_error(std::string("pipe failed: ") + std::strerror(errno));
    }
    const pid_t child = fork();
    if (child < 0) {
        close(pipe_fds[0]);
        close(pipe_fds[1]);
        throw std::runtime_error(std::string("fork failed: ") + std::strerror(errno));
    }
    if (child == 0) {
        dup2(pipe_fds[1], STDERR_FILENO);
        close(pipe_fds[0]);
        close(pipe_fds[1]);
        const std::vector<std::string> args{
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "info",
            "-analyzeduration", "0", "-probesize", "32768", "-fflags", "nobuffer",
            "-flags", "low_delay", "-i", options.url, "-map", "0:v:0", "-vf",
            "showinfo", "-an", "-f", "null", "-"};
        std::vector<char*> argv;
        argv.reserve(args.size() + 1);
        for (const auto& arg : args) {
            argv.push_back(const_cast<char*>(arg.c_str()));
        }
        argv.push_back(nullptr);
        execvp(argv[0], argv.data());
        _exit(127);
    }

    close(pipe_fds[1]);
    std::vector<Sample> samples;
    std::string pending;
    const auto deadline =
        std::chrono::steady_clock::now() + std::chrono::seconds(options.timeout_seconds);
    bool timed_out = false;
    while (samples.size() < options.max_frames) {
        if (std::chrono::steady_clock::now() >= deadline) {
            timed_out = true;
            break;
        }
        pollfd descriptor{pipe_fds[0], POLLIN | POLLHUP, 0};
        const int result = poll(&descriptor, 1, 200);
        if (result < 0) {
            if (errno == EINTR) {
                continue;
            }
            break;
        }
        if (result == 0) {
            continue;
        }
        char buffer[4096];
        const ssize_t count = read(pipe_fds[0], buffer, sizeof(buffer));
        if (count <= 0) {
            break;
        }
        pending.append(buffer, static_cast<std::size_t>(count));
        std::size_t newline;
        while (samples.size() < options.max_frames &&
               (newline = pending.find('\n')) != std::string::npos) {
            std::string line = pending.substr(0, newline);
            pending.erase(0, newline + 1);
            if (!line.empty() && line.back() == '\r') {
                line.pop_back();
            }
            if (line.empty()) {
                continue;
            }
            try {
                const double pts = parse_showinfo_pts(line);
                samples.push_back(make_sample(samples.size(), pts, realtime_ns(),
                                              source_start_ns, pts_origin));
            } catch (const std::exception&) {
                // ffmpeg also emits stream metadata and progress; only showinfo frames count.
            }
        }
    }
    close(pipe_fds[0]);
    kill(child, SIGTERM);
    int status = 0;
    waitpid(child, &status, 0);
    if (samples.empty()) {
        if (timed_out) {
            throw std::runtime_error("timed out before receiving a timestamped video frame");
        }
        if (WIFEXITED(status) && WEXITSTATUS(status) == 127) {
            throw std::runtime_error("ffmpeg is not installed or could not be executed");
        }
        throw std::runtime_error("ffmpeg ended before yielding timestamped video frames");
    }
    return samples;
}

double percentile(std::vector<double> values, double quantile) {
    std::sort(values.begin(), values.end());
    const double position = quantile * static_cast<double>(values.size() - 1);
    const auto lower = static_cast<std::size_t>(std::floor(position));
    const auto upper = static_cast<std::size_t>(std::ceil(position));
    const double fraction = position - static_cast<double>(lower);
    return values[lower] + (values[upper] - values[lower]) * fraction;
}

void write_csv(const std::vector<Sample>& samples, const std::string& path) {
    std::ofstream file;
    std::ostream* output = &std::cout;
    if (path != "-") {
        file.open(path);
        if (!file) {
            throw std::runtime_error("cannot open output file: " + path);
        }
        output = &file;
    }
    *output << "frame,pts_seconds,capture_epoch_ns,receive_epoch_ns,latency_ms\n";
    output->setf(std::ios::fixed);
    *output << std::setprecision(6);
    for (const auto& sample : samples) {
        *output << sample.index << ',' << sample.pts_seconds << ',' << sample.capture_ns
                << ',' << sample.receive_ns << ',' << sample.latency_ms << '\n';
    }
}

void print_summary(const std::vector<Sample>& samples, bool csv_on_stdout) {
    std::vector<double> latencies;
    latencies.reserve(samples.size());
    for (const auto& sample : samples) {
        latencies.push_back(sample.latency_ms);
    }
    std::ostream& output = csv_on_stdout ? std::cerr : std::cout;
    output << std::fixed << std::setprecision(3) << "samples=" << samples.size()
           << " p50_ms=" << percentile(latencies, 0.50)
           << " p95_ms=" << percentile(latencies, 0.95)
           << " p99_ms=" << percentile(latencies, 0.99) << '\n';
}

}  // namespace

int main(int argc, char** argv) {
    try {
        const Options options = parse_options(argc, argv);
        const auto sidecar = read_sidecar(options.sidecar);
        const auto start_it = sidecar.find("source_start_epoch_ns");
        if (start_it == sidecar.end()) {
            throw std::runtime_error("sidecar lacks source_start_epoch_ns");
        }
        const std::int64_t source_start_ns =
            parse_number<std::int64_t>(start_it->second, "source start timestamp");
        double pts_origin = 0.0;
        const auto origin_it = sidecar.find("pts_origin_seconds");
        if (origin_it != sidecar.end()) {
            pts_origin = parse_number<double>(origin_it->second, "PTS origin");
        }

        const auto samples =
            options.url.empty()
                ? read_offline(options, source_start_ns, pts_origin)
                : probe_live(options, source_start_ns, pts_origin);
        if (samples.empty()) {
            throw std::runtime_error("no timestamp samples were produced");
        }
        write_csv(samples, options.output);
        print_summary(samples, options.output == "-");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "latency_probe: " << error.what() << '\n';
        usage(std::cerr);
        return 2;
    }
}
