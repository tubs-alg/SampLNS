#ifndef ALG_SCP_TIMER_HPP
#define ALG_SCP_TIMER_HPP

#include <chrono>

namespace samplns {

class Timer {
public:
  Timer() {
    start();
    stop();
  }

  void start() {
    start_time = std::chrono::high_resolution_clock::now();
    stopped = false;
  }

  void stop() {
    stop_time = std::chrono::high_resolution_clock::now();
    stopped = true;
  }

  /// @brief Returns the elapsed time in seconds, since start() was called.
  /// If stop() was also called, the time in seconds between start() and stop()
  /// is returned.
  /// @return The time in seconds.
  double elapsed() const {
    std::chrono::duration<double> duration;
    if (stopped) {
      duration = stop_time - start_time;
    } else {
      duration = std::chrono::high_resolution_clock::now() - start_time;
    }
    return duration.count();
  }

  /// @brief Returns a timestamp in milliseconds since the epoch. Has nothing to
  /// do with the start and stop of the timer.
  /// @return a 64-bit timestamp
  int64_t timestamp() const {
    auto now = std::chrono::system_clock::now();
    return std::chrono::duration_cast<std::chrono::milliseconds>(
               now.time_since_epoch())
        .count();
  }

private:
  bool stopped = true;
  std::chrono::time_point<std::chrono::high_resolution_clock> start_time;
  std::chrono::time_point<std::chrono::high_resolution_clock> stop_time;
};

} // namespace samplns

#endif
