/**
 * @file _verify.cpp
 * @author Dominik Krupke (krupke@ibr.cs.tu-bs.de)
 * @brief This file is just a quick native checking if two samples have the same
 * coverage. The Python implementation is too slow for larger instances.
 * @version 0.1
 * @date 2023-07-18
 *
 * @copyright Copyright (c) 2023
 *
 */

#include <iostream>
#include <pybind11/functional.h> // automatic conversion of lambdas/functions?
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>        // automatic conversion of vectors

using Sample = std::vector<std::unordered_map<std::string, bool>>;
using IntSample = std::vector<std::vector<bool>>;

bool have_equal_coverage(Sample sample_a, Sample sample_b,
                         std::vector<std::string> concrete_features) {
  if (sample_a.empty() || sample_b.empty()) {
    throw std::invalid_argument("Empty sample.");
  }
  // Convert to int instances for faster comparison
  IntSample int_sample_a;
  IntSample int_sample_b;
  int tuples_covered_by_a = 0;
  int tuples_covered_by_b = 0;
  int tuples_covered_by_both = 0;
  try {
    for (auto &conf : sample_a) {
      std::vector<bool> int_conf;
      for (auto &feature : concrete_features) {
        int_conf.push_back(conf.at(feature));
      }
      int_sample_a.push_back(int_conf);
    }
    for (auto &conf : sample_b) {
      std::vector<bool> int_conf;
      for (auto &feature : concrete_features) {
        int_conf.push_back(conf.at(feature));
      }
      int_sample_b.push_back(int_conf);
    }
  } catch (std::out_of_range &e) {
    throw std::invalid_argument("Sample misses a concrete feature.");
  }
  // check for each tuple if it is covered in both samples
  int n = concrete_features.size();
  for (int v1 = 0; v1 < n; v1++) {
    for (int v2 = v1 + 1; v2 < n; v2++) {
      for (bool v1_val : {true, false}) {
        for (bool v2_val : {true, false}) {
          bool a = false;
          bool b = false;
          for (auto &conf : int_sample_a) {
            if (conf[v1] == v1_val && conf[v2] == v2_val) {
              a = true;
              break;
            }
          }
          if (a) {
            tuples_covered_by_a++;
          }
          for (auto &conf : int_sample_b) {
            if (conf[v1] == v1_val && conf[v2] == v2_val) {
              b = true;
              break;
            }
          }
          if (b) {
            tuples_covered_by_b++;
          }
          if (a || b) {
            tuples_covered_by_both++;
          }
          if (a != b) {
            std::cout << "Number of tuples covered by a: "
                      << tuples_covered_by_a << std::endl;
            std::cout << "Number of tuples covered by b: "
                      << tuples_covered_by_b << std::endl;
            std::cout << "Number of tuples covered by both: "
                      << tuples_covered_by_both << std::endl;
            std::cout << "Missing tuple: " << concrete_features[v1] << "="
                      << v1_val << ", " << concrete_features[v2] << "="
                      << v2_val << std::endl;
            std::cout << "a: " << a << ", b: " << b << std::endl;
            return false;
          }
        }
      }
    }
  }
  std::cout << "Number of tuples covered by a: " << tuples_covered_by_a
            << std::endl;
  std::cout << "Number of tuples covered by b: " << tuples_covered_by_b
            << std::endl;
  std::cout << "Number of tuples covered by both: " << tuples_covered_by_both
            << std::endl;
  return true;
}

PYBIND11_MODULE(_verify, m) {
  namespace py = pybind11;
  m.doc() = "Verify the correctness of a sample.";
  m.def("have_equal_coverage", &have_equal_coverage,
        "Check if two samples have the same coverage.");
}