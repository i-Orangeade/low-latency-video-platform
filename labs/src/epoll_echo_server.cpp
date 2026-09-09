#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <signal.h>
#include <sys/epoll.h>
#include <sys/socket.h>
#include <unistd.h>

#include <algorithm>
#include <array>
#include <charconv>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
#include <system_error>
#include <unordered_map>
#include <utility>

namespace {

volatile sig_atomic_t g_stop = 0;

void on_signal(int) { g_stop = 1; }

class UniqueFd {
 public:
  UniqueFd() = default;
  explicit UniqueFd(int fd) : fd_(fd) {}
  ~UniqueFd() {
    if (fd_ >= 0) {
      ::close(fd_);
    }
  }

  UniqueFd(const UniqueFd&) = delete;
  UniqueFd& operator=(const UniqueFd&) = delete;

  UniqueFd(UniqueFd&& other) noexcept : fd_(std::exchange(other.fd_, -1)) {}
  UniqueFd& operator=(UniqueFd&& other) noexcept {
    if (this != &other) {
      if (fd_ >= 0) {
        ::close(fd_);
      }
      fd_ = std::exchange(other.fd_, -1);
    }
    return *this;
  }

  int get() const { return fd_; }

 private:
  int fd_ = -1;
};

[[noreturn]] void throw_system_error(const char* operation) {
  throw std::system_error(errno, std::generic_category(), operation);
}

struct Connection {
  explicit Connection(UniqueFd fd_value) : fd(std::move(fd_value)) {}

  UniqueFd fd;
  std::string pending;
  std::size_t write_offset = 0;
  bool peer_closed = false;

  std::size_t queued_bytes() const { return pending.size() - write_offset; }
};

class EchoServer {
 public:
  EchoServer(std::uint16_t port, std::size_t high_watermark)
      : high_watermark_(high_watermark),
        low_watermark_(high_watermark / 2),
        hard_limit_(high_watermark * 4) {
    const int listen_fd =
        ::socket(AF_INET, SOCK_STREAM | SOCK_NONBLOCK | SOCK_CLOEXEC, 0);
    if (listen_fd < 0) {
      throw_system_error("socket");
    }
    listener_ = UniqueFd(listen_fd);

    int enabled = 1;
    if (::setsockopt(listener_.get(), SOL_SOCKET, SO_REUSEADDR, &enabled,
                     sizeof(enabled)) < 0) {
      throw_system_error("setsockopt");
    }

    sockaddr_in address{};
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = htonl(INADDR_ANY);
    address.sin_port = htons(port);
    if (::bind(listener_.get(), reinterpret_cast<sockaddr*>(&address),
               sizeof(address)) < 0) {
      throw_system_error("bind");
    }
    if (::listen(listener_.get(), SOMAXCONN) < 0) {
      throw_system_error("listen");
    }

    const int epoll_fd = ::epoll_create1(EPOLL_CLOEXEC);
    if (epoll_fd < 0) {
      throw_system_error("epoll_create1");
    }
    epoll_ = UniqueFd(epoll_fd);
    add_epoll(listener_.get(), EPOLLIN);
  }

  void run() {
    std::array<epoll_event, 128> events{};
    while (!g_stop) {
      const int ready =
          ::epoll_wait(epoll_.get(), events.data(), events.size(), 1000);
      if (ready < 0) {
        if (errno == EINTR) {
          continue;
        }
        throw_system_error("epoll_wait");
      }
      for (int index = 0; index < ready; ++index) {
        const int fd = events[index].data.fd;
        const std::uint32_t flags = events[index].events;
        if (fd == listener_.get()) {
          accept_connections();
        } else {
          service_connection(fd, flags);
        }
      }
    }
  }

 private:
  void add_epoll(int fd, std::uint32_t events) {
    epoll_event event{};
    event.events = events;
    event.data.fd = fd;
    if (::epoll_ctl(epoll_.get(), EPOLL_CTL_ADD, fd, &event) < 0) {
      throw_system_error("epoll_ctl ADD");
    }
  }

  bool update_interest(Connection& connection) {
    if (connection.peer_closed && connection.queued_bytes() == 0) {
      return false;
    }

    std::uint32_t events = EPOLLRDHUP;
    if (!connection.peer_closed &&
        connection.queued_bytes() < high_watermark_) {
      events |= EPOLLIN;
    }
    if (connection.queued_bytes() > 0) {
      events |= EPOLLOUT;
    }

    epoll_event event{};
    event.events = events;
    event.data.fd = connection.fd.get();
    return ::epoll_ctl(epoll_.get(), EPOLL_CTL_MOD, connection.fd.get(),
                       &event) == 0;
  }

  void accept_connections() {
    for (;;) {
      sockaddr_in peer{};
      socklen_t peer_size = sizeof(peer);
      const int client =
          ::accept4(listener_.get(), reinterpret_cast<sockaddr*>(&peer),
                    &peer_size, SOCK_NONBLOCK | SOCK_CLOEXEC);
      if (client < 0) {
        if (errno == EAGAIN || errno == EWOULDBLOCK) {
          return;
        }
        if (errno == EINTR || errno == ECONNABORTED) {
          continue;
        }
        std::cerr << "accept4: " << std::strerror(errno) << '\n';
        return;
      }

      UniqueFd accepted(client);
      try {
        add_epoll(client, EPOLLIN | EPOLLRDHUP);
        connections_.emplace(client, Connection(std::move(accepted)));
      } catch (...) {
        ::epoll_ctl(epoll_.get(), EPOLL_CTL_DEL, client, nullptr);
        throw;
      }
    }
  }

  bool read_available(Connection& connection) {
    std::array<char, 64 * 1024> buffer{};
    while (connection.queued_bytes() < high_watermark_) {
      const std::size_t room = hard_limit_ - connection.queued_bytes();
      if (room == 0) {
        return false;
      }
      const std::size_t request = std::min(buffer.size(), room);
      const ssize_t count =
          ::recv(connection.fd.get(), buffer.data(), request, 0);
      if (count > 0) {
        connection.pending.append(buffer.data(),
                                  static_cast<std::size_t>(count));
        continue;
      }
      if (count == 0) {
        connection.peer_closed = true;
        break;
      }
      if (errno == EAGAIN || errno == EWOULDBLOCK) {
        break;
      }
      if (errno == EINTR) {
        continue;
      }
      return false;
    }
    return true;
  }

  bool write_available(Connection& connection) {
    while (connection.queued_bytes() > 0) {
      const char* data = connection.pending.data() + connection.write_offset;
      const ssize_t count =
          ::send(connection.fd.get(), data, connection.queued_bytes(),
                 MSG_NOSIGNAL);
      if (count > 0) {
        connection.write_offset += static_cast<std::size_t>(count);
        continue;
      }
      if (count < 0 && errno == EINTR) {
        continue;
      }
      if (count < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
        break;
      }
      return false;
    }

    if (connection.write_offset == connection.pending.size()) {
      connection.pending.clear();
      connection.write_offset = 0;
    } else if (connection.write_offset > low_watermark_) {
      connection.pending.erase(0, connection.write_offset);
      connection.write_offset = 0;
    }
    return true;
  }

  void service_connection(int fd, std::uint32_t events) {
    auto iterator = connections_.find(fd);
    if (iterator == connections_.end()) {
      return;
    }
    Connection& connection = iterator->second;

    bool healthy = (events & EPOLLERR) == 0;
    if (healthy && (events & (EPOLLIN | EPOLLRDHUP | EPOLLHUP)) != 0) {
      healthy = read_available(connection);
    }
    if (healthy && connection.queued_bytes() > 0) {
      healthy = write_available(connection);
    }
    if (healthy) {
      healthy = update_interest(connection);
    }
    if (!healthy) {
      ::epoll_ctl(epoll_.get(), EPOLL_CTL_DEL, fd, nullptr);
      connections_.erase(iterator);
    }
  }

  UniqueFd listener_;
  UniqueFd epoll_;
  std::unordered_map<int, Connection> connections_;
  const std::size_t high_watermark_;
  const std::size_t low_watermark_;
  const std::size_t hard_limit_;
};

std::uint16_t parse_port(const char* text) {
  unsigned int value = 0;
  const char* end = text + std::strlen(text);
  const auto result = std::from_chars(text, end, value);
  if (result.ec != std::errc{} || result.ptr != end || value == 0 ||
      value > 65535) {
    throw std::invalid_argument("port must be in 1..65535");
  }
  return static_cast<std::uint16_t>(value);
}

}  // namespace

int main(int argc, char** argv) {
  try {
    if (argc > 3) {
      std::cerr << "usage: " << argv[0] << " [port] [high-watermark-bytes]\n";
      return EXIT_FAILURE;
    }
    const std::uint16_t port = argc >= 2 ? parse_port(argv[1]) : 9000;
    std::size_t high_watermark = 256 * 1024;
    if (argc == 3) {
      const char* end = argv[2] + std::strlen(argv[2]);
      const auto result =
          std::from_chars(argv[2], end, high_watermark);
      if (result.ec != std::errc{} || result.ptr != end ||
          high_watermark < 1024) {
        throw std::invalid_argument("high watermark must be at least 1024");
      }
    }

    struct sigaction action {};
    action.sa_handler = on_signal;
    ::sigemptyset(&action.sa_mask);
    ::sigaction(SIGINT, &action, nullptr);
    ::sigaction(SIGTERM, &action, nullptr);
    ::signal(SIGPIPE, SIG_IGN);

    EchoServer server(port, high_watermark);
    std::cout << "listening on 0.0.0.0:" << port
              << ", high_watermark=" << high_watermark << '\n';
    std::cout.flush();
    server.run();
    return EXIT_SUCCESS;
  } catch (const std::exception& error) {
    std::cerr << "fatal: " << error.what() << '\n';
    return EXIT_FAILURE;
  }
}
