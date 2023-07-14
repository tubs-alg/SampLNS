#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include <mutex>
#include <functional>
#include <fmt/core.h>

/// The LogHandler type represents a callback method that can be registered at a Logger class
/// object. It takes a single parameter, a constant reference to a `std::string` representing a log
/// message. The user can define their own implementation of the `LogHandler` callback to react to
/// log messages and perform actions such as writing or printing them to a desired location.
typedef std::function<void(const std::string& msg)> LogHandler;

/// @brief A simple, threadsafe logger class, which can be muted, unmuted and configured to write to multiple output streams and handlers.
class Logger {
public:
    /// @brief Create a new logger with the given name.
    Logger(const std::string& name) {
        this->set_name(name);
    }

    /// @brief Sets the name of the current logger to the specified name.
    /// @param name The new name of the logger.
    Logger& set_name(const std::string& name) {
        this->name = name;
    }

    /// @brief Convenience method for adding stdout to the list of output streams.
    /// @return This logger. Can be used to register multiple streams sequentially.
    Logger& add_stdout() {
        this->add_ostream(&std::cout);
        return *this;
    }

    /// @brief Adds a stream to the list of output streams.
    /// @param stream Pointer to the stream to be added. Make sure that the stream does not get out of scope.
    /// @return This logger. Can be used to register multiple streams sequentially.
    Logger& add_ostream(std::ostream* stream) {
        // Create a LogHandler as "adapter" to the given stream.
        // The pointer to the stream is copied.
        LogHandler stream_logger = [=](const std::string& msg) {
            *stream << msg;
        };
        std::unique_lock(output_lock);
        handlers.emplace_back(stream_logger);
        return *this;
    }

    /// @brief Logs a formatted message using the provided format string and arguments.
    /// This method takes a format string with placeholder symbols (see fmt) and a variable number of arguments.
    /// @param fmt_str The format string specifying the log message format.
    /// @param args The arguments to be inserted into the format string.
    ///
    template <typename... T>
    inline void logf(const std::string& fmt_str, T&&... args) {
        this->log(fmt::format(fmt_str, args));
    }

    /// @brief Log the provided string to all registered log handlers.
    /// @param str The string to be logged.
    void log(const std::string& str) {
        if (this->muted) {
            return;
        }
        std::string msg = fmt::format("[{0}]: {1}", this->name, str);
        std::unique_lock(output_lock);
        for (auto& handler : handlers) {
            handler(msg);
        }
    }

    /// @brief Mute the logger. All further calls to log() or the << operator will be ignored, until unmuted.
    void mute() {
        muted = true;
    }

    /// @brief Unmute the logger.
    void unmute() {
        muted = false;
    }

private:
    std::string name = "Logger-" + std::to_string(reinterpret_cast<std::uintptr_t>(this));
    bool muted = false;
    std::vector<LogHandler> handlers;
    std::mutex output_lock;
};