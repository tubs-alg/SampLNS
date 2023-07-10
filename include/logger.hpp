#include <filesystem>
#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <mutex>

namespace fs = std::filesystem;

/// @brief A simple, threadsafe logger class, which can be muted, unmuted and configured to write to multiple output streams.
class Logger {
public:
    /// @brief Create a new logger, which does not write to any stream. It is essentially mute (but not explicitly muted).
    Logger() {}

    /// @brief Create a new logger with the single given output stream.
    /// @param ostream 
    Logger(std::ostream* ostream) {
        this->add_ostream(ostream);
    }

    /// @brief Log a value in std::ostream style.
    /// @tparam T the object type of the value parameter.
    /// @param value The value to log. Can, but must not be a string.
    /// @return This logger. Can be used to log multiple values sequentially.
    template<typename T>
    Logger& operator<<(const T& value) {
        if (!muted && !outputs.empty()) {
            // buffer the value, log the buffered string
            std::ostringstream buf;
            buf << value;
            this->log(buf.str())
        }
        return *this;
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
        std::unique_lock(output_lock);
        outputs.push_back(stream);
        return *this;
    }

    /// @brief Adds a file output stream to the list of output streams.
    /// @param path The file to be written to. 
    /// @param open_mode The open mode for the file. Default is append (std::ios_base::app).
    /// @return This logger. Can be used to register multiple streams sequentially.
    Logger& add_file(const std::string &path, std::ios_base::openmode open_mode = std::ios_base::app) {
        fs::path fp(path);

        if (fs::is_directory(fp)) {
            throw std::runtime_error(path + " is a directory!");
        }

        // open file in append mode
        std::ofstream* out_file = new std::ofstream();
        out_file->open(fp, open_mode);
        if (out_file->fail()) {
            throw std::runtime_error("Failed to open file " + path + "!");
        }

        // add file stream to outputs
        std::unique_lock(output_lock);
        outputs.push_back(out_file);

        return *this;
    }

    /// @brief Logs a string to all registered output streams.
    /// @param str The string to be logged.
    void log(const std::string& str) {
        std::unique_lock(output_lock);
        for (auto& output : outputs) {
            *output << str;
        }
    }

    /// @brief Mutes the logger. All further calls to log() or the << operator will be ignored, until unmuted.
    void mute() {
        muted = true;
    }

    /// @brief Unmute the logger.
    void unmute() {
        muted = false;
    }

private:
    bool muted = false;
    std::vector<std::ostream*> outputs;
    std::mutex output_lock;
};