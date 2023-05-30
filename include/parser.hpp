#ifndef ALG_SCP_INSTANCE_PARSER_HPP
#define ALG_SCP_INSTANCE_PARSER_HPP

#include <exception>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include "instance.hpp"
#include "nlohmann/json.hpp"

namespace samplns {
using json = nlohmann::json;
namespace fs = std::filesystem;

class InstanceParser {
public:
  static Instance load(const std::string &path) {
    fs::path instance_dir(path);

    if (!fs::exists(instance_dir)) {
      throw std::runtime_error(path + " is not a valid path!");
    }

    if (!fs::is_directory(instance_dir)) {
      throw std::runtime_error(path + " is not a directory!");
    }

    Instance instance;

    for (const auto &entry : fs::directory_iterator(instance_dir)) {
      const auto &file = entry.path();
      const std::string filename = file.filename();
      if (fs::is_directory(file)) {
        std::cout << "Warning: Ignored unexpected directory \"" + filename +
                         "\" in instance directory."
                  << std::endl;
        continue;
      }

      std::ifstream f(file);

      if (filename == "conflicts.json") {
        const json data = json::parse(f);
        instance.conflicts = data["conflicts"].get<std::vector<feature_pair>>();
      } else if (filename == "index_instance.json") {
        const json data = json::parse(f);
        instance.name = data["name"].get<std::string>();
        instance.n_all = data["n_all"].get<std::uint64_t>();
        instance.n_concrete = data["n_concrete"].get<std::uint64_t>();
        // this file also contains the entire feature tree, which is not needed
        // for now
      } else if (filename == "initial.json") {
        const json data = json::parse(f);
        instance.sample =
            data["initial_sample"].get<std::vector<configuration>>();
        instance.mutually_exclusive_set = data["initial_mutually_exclusive_set"]
                                              .get<std::vector<feature_pair>>();
      } else if (filename == "sat_encoding.json") {
        const json data = json::parse(f);
        instance.clauses = data["clauses"].get<std::vector<clause>>();
      } else {
        std::cout << "Warning: Ignored unexpected file \"" + filename +
                         "\" in instance directory."
                  << std::endl;
      }
    }

    return instance;
  }
};
} // namespace samplns

#endif
