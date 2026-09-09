#include <charconv>
#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <deque>
#include <iostream>
#include <mutex>
#include <stdexcept>
#include <string>
#include <thread>
#include <utility>
#include <vector>

namespace {

template <typename T>
class BoundedQueue {
 public:
  explicit BoundedQueue(std::size_t capacity) : capacity_(capacity) {
    if (capacity == 0) {
      throw std::invalid_argument("queue capacity must be positive");
    }
  }

  BoundedQueue(const BoundedQueue&) = delete;
  BoundedQueue& operator=(const BoundedQueue&) = delete;

  bool push(T value) {
    std::unique_lock<std::mutex> lock(mutex_);
    not_full_.wait(lock,
                   [this] { return queue_.size() < capacity_ || closed_; });
    if (closed_) {
      return false;
    }
    queue_.push_back(std::move(value));
    not_empty_.notify_one();
    return true;
  }

  bool pop(T& value) {
    std::unique_lock<std::mutex> lock(mutex_);
    not_empty_.wait(lock, [this] { return !queue_.empty() || closed_; });
    if (queue_.empty()) {
      return false;
    }
    value = std::move(queue_.front());
    queue_.pop_front();
    not_full_.notify_one();
    return true;
  }

  void close() {
    {
      std::lock_guard<std::mutex> lock(mutex_);
      closed_ = true;
    }
    not_empty_.notify_all();
    not_full_.notify_all();
  }

 private:
  const std::size_t capacity_;
  std::mutex mutex_;
  std::condition_variable not_empty_;
  std::condition_variable not_full_;
  std::deque<T> queue_;
  bool closed_ = false;
};

struct Item {
  std::size_t producer;
  std::size_t sequence;
};

std::size_t parse_positive(const char* text, const char* name) {
  std::size_t value = 0;
  const char* end = text;
  while (*end != '\0') {
    ++end;
  }
  const auto result = std::from_chars(text, end, value);
  if (result.ec != std::errc{} || result.ptr != end || value == 0) {
    throw std::invalid_argument(std::string(name) + " must be positive");
  }
  return value;
}

}  // namespace

int main(int argc, char** argv) {
  try {
    if (argc > 5) {
      std::cerr << "usage: " << argv[0]
                << " [producers] [consumers] [items-per-producer] [capacity]\n";
      return EXIT_FAILURE;
    }
    const std::size_t producer_count =
        argc >= 2 ? parse_positive(argv[1], "producers") : 4;
    const std::size_t consumer_count =
        argc >= 3 ? parse_positive(argv[2], "consumers") : 3;
    const std::size_t items_per_producer =
        argc >= 4 ? parse_positive(argv[3], "items-per-producer") : 100000;
    const std::size_t capacity =
        argc >= 5 ? parse_positive(argv[4], "capacity") : 64;

    BoundedQueue<Item> queue(capacity);
    std::vector<std::thread> producers;
    std::vector<std::thread> consumers;
    std::vector<std::uint64_t> consumer_counts(consumer_count);
    std::vector<std::uint64_t> consumer_sums(consumer_count);

    for (std::size_t id = 0; id < consumer_count; ++id) {
      consumers.emplace_back([&, id] {
        Item item{};
        while (queue.pop(item)) {
          ++consumer_counts[id];
          consumer_sums[id] +=
              item.producer * items_per_producer + item.sequence;
        }
      });
    }
    for (std::size_t id = 0; id < producer_count; ++id) {
      producers.emplace_back([&, id] {
        for (std::size_t sequence = 0; sequence < items_per_producer;
             ++sequence) {
          if (!queue.push(Item{id, sequence})) {
            throw std::runtime_error("queue closed while producers active");
          }
        }
      });
    }

    for (auto& producer : producers) {
      producer.join();
    }
    queue.close();
    for (auto& consumer : consumers) {
      consumer.join();
    }

    std::uint64_t actual_count = 0;
    std::uint64_t actual_sum = 0;
    for (std::size_t id = 0; id < consumer_count; ++id) {
      actual_count += consumer_counts[id];
      actual_sum += consumer_sums[id];
    }
    const std::uint64_t expected_count =
        producer_count * items_per_producer;
    const std::uint64_t expected_sum =
        expected_count * (expected_count - 1) / 2;

    std::cout << "produced=" << expected_count
              << " consumed=" << actual_count << " sum=" << actual_sum
              << " expected_sum=" << expected_sum << '\n';
    if (actual_count != expected_count || actual_sum != expected_sum) {
      std::cerr << "validation failed\n";
      return EXIT_FAILURE;
    }
    std::cout << "validation=ok\n";
    return EXIT_SUCCESS;
  } catch (const std::exception& error) {
    std::cerr << "fatal: " << error.what() << '\n';
    return EXIT_FAILURE;
  }
}
