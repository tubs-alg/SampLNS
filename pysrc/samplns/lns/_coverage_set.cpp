#include <pybind11/functional.h> // automatic conversion of lambdas/functions?
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>        // automatic conversion of vectors

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
      if(conf.size() != this->num_concrete_features) {
        throw std::invalid_argument("The number of concrete features in the initial sample does not match the number of concrete features in the graph.");
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

  ~CoveredTuples() {}

  bool is_contained(int f1, bool v1, int f2, bool v2) {
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

  int get_index(int f, bool val) { return 2 * f + (val ? 1 : 0); }

  std::pair<int, bool> get_feature_and_value(int index) {
    return std::make_pair(index / 2, index % 2 == 1);
  }

  std::vector<std::vector<bool>> feasibility_matrix;
};

class CoverageSet {
public:
  CoverageSet(CoveredTuples feasible_tuples)
      : feasible_tuples{feasible_tuples}, covered_tuples{feasible_tuples.num_concrete_features} {}

  ~CoverageSet() {}

  void add_configuration(const std::vector<bool> &conf) {
    this->covered_tuples.add_tuples_of_configuration(conf);
  }

  int num_missing_tuples() {
    return this->feasible_tuples.num_covered_tuples -
           this->covered_tuples.num_covered_tuples;
  }

  void clear() { this->covered_tuples = CoveredTuples{this->feasible_tuples.num_concrete_features}; }

  std::vector<std::pair<std::pair<int, bool>, std::pair<int, bool>>> get_missing_tuples() {
    std::vector<std::pair<std::pair<int, bool>, std::pair<int, bool>>> missing_tuples;
    for (int i = 0; i < this->feasible_tuples.num_concrete_features; i++) {
      for (int j = i + 1; j < this->feasible_tuples.num_concrete_features; j++) {
        if (this->feasible_tuples.is_contained(i, true, j, true) && !this->covered_tuples.is_contained(i, true, j, true)) {
          missing_tuples.push_back(std::make_pair(
              std::make_pair(i, true), std::make_pair(j, true)));
        }
        if (this->feasible_tuples.is_contained(i, true, j, false) && !this->covered_tuples.is_contained(i, true, j, false)) {
          missing_tuples.push_back(std::make_pair(
              std::make_pair(i, true), std::make_pair(j, false)));
        }
        if (this->feasible_tuples.is_contained(i, false, j, true) && !this->covered_tuples.is_contained(i, false, j, true)) {
          missing_tuples.push_back(std::make_pair(
              std::make_pair(i, false), std::make_pair(j, true)));
        }
        if (this->feasible_tuples.is_contained(i, false, j, false) &&  !this->covered_tuples.is_contained(i, false, j, false)) {
          missing_tuples.push_back(std::make_pair(
              std::make_pair(i, false), std::make_pair(j, false)));
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
      .def_readonly("num_concrete_features",
                    &CoveredTuples::num_concrete_features)
      .def_readonly("num_covered_tuples",
                    &CoveredTuples::num_covered_tuples);
  py::class_<CoverageSet>(m, "CoverageSet").def(py::init<CoveredTuples>())
      .def("add_configuration", &CoverageSet::add_configuration)
      .def("num_missing_tuples", &CoverageSet::num_missing_tuples)
      .def("clear", &CoverageSet::clear)
      .def("get_missing_tuples", &CoverageSet::get_missing_tuples);
}