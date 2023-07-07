//
// Created by Dominik Krupke on 03.12.22.
//

#include "cds/cds.hpp"
#include "cds/cds_greedy.hpp"
#include "cds/cds_heuristic.hpp"
#include "cds/cds_ip.hpp"
#include "graph.hpp"
#include <fmt/core.h>
#include <pybind11/functional.h> // automatic conversion of lambdas/functions?
#include <pybind11/iostream.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h> // automatic conversion of vectors

static const std::vector<Edge> FULL_GRAPH = {};

PYBIND11_MODULE(_cds_bindings, m) {
  namespace py = pybind11;
  using namespace samplns;

  // Redirecting stdout/stderr to python
  // https://pybind11.readthedocs.io/en/stable/advanced/pycpp/utilities.html#capturing-standard-output-from-ostream
  py::add_ostream_redirect(m, "ostream_redirect");

  // Transaction Graph
  py::class_<TransactionGraph>(m, "TransactionGraph",
                               "Graph of feasible feature literal pairs.")
      .def(py::init<uint64_t>())
      .def("add_edge", &TransactionGraph::add_edge)
      .def("has_edge", &TransactionGraph::has_edge)
      .def("remove_edge", &TransactionGraph::remove_edge)
      .def("count_edges", &TransactionGraph::count_edges)
      .def("add_valid_configuration",
           &TransactionGraph::add_valid_configuration)
      .def("from_conflicts", &TransactionGraph::from_conflicts)
      .def("are_edges_clique_disjoint",
           [&](const TransactionGraph *graph,
               const std::vector<feature_pair> cds) {
             graph->are_edges_clique_disjoint(cds);
           });

  // CDS Solver
  py::class_<CDSSolverInterface>(
      m, "LnsCds", "A large neighborhood search algorithm for computing a CDS")
      .def(py::init<TransactionGraph *, std::vector<Edge>, bool, bool>(),
           py::arg("graph"), py::arg("subgraph") = FULL_GRAPH,
           py::arg("use_heur") = true,
           py::arg("be_smart") = true) // size constructor
      .def("optimize", &CDSSolverInterface::optimize,
           py::arg("initial_solution"), py::arg("max_iterations") = 15,
           py::arg("time_limit") = 60.0, py::arg("verbose") = false)
      .def("get_iteration_statistics",
           &CDSSolverInterface::get_iteration_statistics);

  // Async CDS solver
  py::class_<AsyncCDSSolverInterface>(
      m, "AsyncLnsCds",
      "A large neighborhood search algorithm for computing a CDS")
      .def(py::init<TransactionGraph *>())
      .def("get_best_solution", &AsyncCDSSolverInterface::get_best_solution)
      .def("get_iteration_statistics",
           &AsyncCDSSolverInterface::get_iteration_statistics)
      .def("start", &AsyncCDSSolverInterface::start,
           py::arg("initial_solution"), py::arg("time_limit") = 60.0)
      .def("stop", &AsyncCDSSolverInterface::stop);

  // Heuristic Solver (exposed for experiments)
  py::class_<CDSNodeHeuristic>(
      m, "CDSNodeHeuristic",
      "A large neighborhood search algorithm for computing a CDS")
      .def(py::init<const TransactionGraph &,
                    const std::vector<feature_pair> &>())
      .def("get_best_solution", &CDSNodeHeuristic::get_best_solution)
      .def("optimize", &CDSNodeHeuristic::optimize)
      .def("get_iteration_statistics",
           &CDSNodeHeuristic::get_iteration_statistics);

  // greedy solver
  py::class_<GreedyCDS>(m, "GreedyCds",
                        "A greedy search algorithm for computing a CDS")
      .def(py::init<const TransactionGraph &,
                    const std::vector<std::vector<feature_id>> &>())
      .def("optimize", &GreedyCDS::optimize);

  // FeatureTuple
  py::class_<FeatureTuple>(m, "FeatureTuple")
      .def(py::init<feature_id, feature_id>())
      .def_readonly("first", &FeatureTuple::first)
      .def_readonly("second", &FeatureTuple::second)
      .def("__eq__",
           [](const FeatureTuple &t1, const FeatureTuple &t2) {
             return t1.first == t2.first && t1.second == t2.second;
           })
      .def("__len__", [](const FeatureTuple &t) { return 2; })
      .def("__getitem__",
           [](const FeatureTuple &t, int i) {
             if (i == 0)
               return t.first;
             else if (i == 1)
               return t.second;
             else
               throw py::index_error();
           })
      .def("__repr__", [](const FeatureTuple &t) {
        return fmt::format("({}, {})", t.first, t.second);
      });

  // gurobi exception
  static py::exception<GRBException> exc(m, "GRBException");
  py::register_exception_translator([](std::exception_ptr p) {
    try {
      if (p)
        std::rethrow_exception(p);
    } catch (const GRBException &e) {
      auto msg = e.getMessage();
      exc(msg.c_str());
    }
  });
}
