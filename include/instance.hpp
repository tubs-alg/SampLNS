#ifndef ALG_SCP_INSTANCE_HPP
#define ALG_SCP_INSTANCE_HPP

#include "nlohmann/json.hpp"
#include <string>
#include <utility>
#include <vector>

namespace samplns {
using json = nlohmann::json;

using feature_id = int32_t; // used for encoding literals. -v is the negated
                            // literal, v the positive
static_assert(std::is_signed<feature_id>());

using feature_pair =
    std::pair<feature_id,
              feature_id>; // used for encoding pairs of literals. May represent
                           // an edge in a literal graph or just "coordinates"
using configuration = std::vector<feature_id>; // a list of feature id's can be
                                               // considered a configuration
using clause = std::vector<feature_id>;        // a vector of literals can be
                                        // considered a clause (for sat clauses)

struct Instance {
  std::string name;
  std::vector<feature_pair> conflicts;
  std::uint64_t n_all;
  std::uint64_t n_concrete;
  std::vector<configuration> sample;
  std::vector<feature_pair> mutually_exclusive_set;
  std::vector<clause> clauses;

  json to_json() {
    json data = {{"name", this->name},
                 {"n_all", this->n_all},
                 {"n_concrete", this->n_concrete},
                 {"conflicts", this->conflicts},
                 {"sample", this->sample},
                 {"mutually_exclusive_set", this->mutually_exclusive_set},
                 {"clauses", this->clauses}};
    return data;
  }
};
} // namespace samplns

// hash functions for data types

template <> struct std::hash<samplns::feature_pair> {
  size_t operator()(const samplns::feature_pair &e) const {
    size_t hashcode = 17;
    hashcode = 31 * hashcode + e.first;
    hashcode = 31 * hashcode + e.second;
    return hashcode;
  }
};

template <> struct std::hash<std::vector<samplns::feature_pair>> {
  size_t operator()(const std::vector<samplns::feature_pair> &sol) const {
    size_t hashcode = 0xF0F0F0F0;
    for (const auto &e : sol) {
      hashcode ^= std::hash<samplns::feature_pair>()(e);
    }
    return hashcode;
  }
};

#endif
