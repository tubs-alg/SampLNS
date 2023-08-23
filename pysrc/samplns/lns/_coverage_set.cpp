/**
 * @file _coverage_set.cpp
 * @author Dominik Krupke
 * @brief This file implements a native implementation for checking which feature tuples are covered by a given sample. This is used to check which
 * tuples are missing in a given sample for the Large Neighborhood Search. Previously implemented in Python but it was too slower for larger instances.
 * @version 0.1
 * @date 2023-07-13
 *
 * @copyright Copyright (c) 2023
 *
 */

#include <pybind11/functional.h> // automatic conversion of lambdas/functions?
#include <pybind11/pybind11.h>
#include <pybind11/stl.h> // automatic conversion of vectors

class CoveredTuples {
public:
  CoveredTuples(int num_concrete_features) {
    this->num_concrete_features = num_concrete_features;
    this->set_up_matrix();
  }

  CoveredTuples(const std::vector<std::vector<bool>> &initial_sample,
                int num_concrete_features) {

    this->num_concrete_features = num_concrete_features;
    this->set_up_matrix();
    for (const auto &conf : initial_sample) {
      if (conf.size() != this->num_concrete_features) {
        throw std::invalid_argument(
            "The number of concrete features in the initial sample does not "
            "match the number of concrete features in the graph.");
      }
      this->add_tuples_of_configuration(conf);
    }
  }

  void add_tuples_of_configuration(const std::vector<bool> &conf) {
    for (int i = 0; i < this->num_concrete_features; i++) {
      for (int j = i + 1; j < this->num_concrete_features; j++) {
        this->set_feasible(i, conf[i], j, conf[j]);
      }
    }
  }

  bool operator==(const CoveredTuples &other) const {
    return this->feasibility_matrix == other.feasibility_matrix;
  }

  bool operator<=(const CoveredTuples &other) const {
    for (int i = 0; i < 2 * this->num_concrete_features; i++) {
      for (int j = 0; j < 2 * this->num_concrete_features; j++) {
        if (this->feasibility_matrix[i][j] && !other.feasibility_matrix[i][j]) {
          return false;
        }
      }
    }
    return true;
  }

  ~CoveredTuples() {}

  bool is_contained(int f1, bool v1, int f2, bool v2) const {
    return this->feasibility_matrix[get_index(f1, v1)][get_index(f2, v2)];
  }

  int num_concrete_features;
  int num_covered_tuples = 0;

private:
  void set_up_matrix() {
    this->feasibility_matrix.clear();
    this->feasibility_matrix.reserve(2 * num_concrete_features);
    for (int i = 0; i < 2 * num_concrete_features; i++) {
      this->feasibility_matrix.push_back(
          std::vector<bool>(2 * num_concrete_features, false));
    }
  }

  void set_feasible(int f1, bool v1, int f2, bool v2) {
    if (this->feasibility_matrix[get_index(f1, v1)][get_index(f2, v2)]) {
      return;
    }
    this->feasibility_matrix[get_index(f1, v1)][get_index(f2, v2)] = true;
    this->feasibility_matrix[get_index(f2, v2)][get_index(f1, v1)] = true;
    this->num_covered_tuples++;
  }

  int get_index(int f, bool val)  const{ return 2 * f + (val ? 1 : 0); }

  std::pair<int, bool> get_feature_and_value(int index) {
    return std::make_pair(index / 2, index % 2 == 1);
  }

  std::vector<std::vector<bool>> feasibility_matrix;
};

class CoverageSet {
public:
  CoverageSet(CoveredTuples feasible_tuples)
      : feasible_tuples{feasible_tuples},
        covered_tuples{feasible_tuples.num_concrete_features} {}

  ~CoverageSet() {}

  void add_configuration(const std::vector<bool> &conf) {
    this->covered_tuples.add_tuples_of_configuration(conf);
    if(this->is_configuration_contradicting(conf)){
      throw std::runtime_error("The covered tuples are not a subset of the "
                               "feasible tuples!");
    }
  }

  bool is_configuration_contradicting(const std::vector<bool> &conf) const {
    for (int i = 0; i < this->feasible_tuples.num_concrete_features; i++) {
      for (int j = i + 1; j < this->feasible_tuples.num_concrete_features; j++) {
        if(!this->feasible_tuples.is_contained(i, conf[i], j, conf[j])){
          return true;  // contradiction found, configuration is invalid
        }
      }
    }
    return false;
  }

  int num_missing_tuples() {
    return this->feasible_tuples.num_covered_tuples -
           this->covered_tuples.num_covered_tuples;
  }

  void clear() {
    this->covered_tuples =
        CoveredTuples{this->feasible_tuples.num_concrete_features};
  }

  std::vector<std::pair<std::pair<int, bool>, std::pair<int, bool>>>
  get_missing_tuples() {
    std::vector<std::pair<std::pair<int, bool>, std::pair<int, bool>>>
        missing_tuples;
    for (int i = 0; i < this->feasible_tuples.num_concrete_features; i++) {
      for (int j = i + 1; j < this->feasible_tuples.num_concrete_features;
           j++) {
          for (bool i_val: {true, false}){
            for (bool j_val: {true, false}){
              if(this->feasible_tuples.is_contained(i, i_val, j, j_val) &&
                  !this->covered_tuples.is_contained(i, i_val, j, j_val)){
                missing_tuples.push_back(std::make_pair(std::make_pair(i, i_val),
                                                        std::make_pair(j, j_val)));
              }
            }
          }
      }
    }
    return missing_tuples;
  }

private:
  CoveredTuples feasible_tuples;
  CoveredTuples covered_tuples;
};

PYBIND11_MODULE(_coverage_set, m) {
  namespace py = pybind11;
  py::class_<CoveredTuples>(m, "CoveredTuples")
      .def(py::init<const std::vector<std::vector<bool>> &, int>())
      .def("is_contained", &CoveredTuples::is_contained)
      .def("__eq__", &CoveredTuples::operator==)
      .def("__le__", &CoveredTuples::operator<=)
      .def_readonly("num_concrete_features",
                    &CoveredTuples::num_concrete_features)
      .def_readonly("num_covered_tuples", &CoveredTuples::num_covered_tuples);
  py::class_<CoverageSet>(m, "CoverageSet")
      .def(py::init<CoveredTuples>())
      .def("add_configuration", &CoverageSet::add_configuration)
      .def("num_missing_tuples", &CoverageSet::num_missing_tuples)
      .def("clear", &CoverageSet::clear)
      .def("get_missing_tuples", &CoverageSet::get_missing_tuples);
}
