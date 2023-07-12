#ifndef ALG_SCP_CDS_IP_HPP
#define ALG_SCP_CDS_IP_HPP

#include "../graph.hpp"
#include "../instance.hpp"
#include "gurobi_c++.h"
#include <chrono>
#include <fmt/core.h>
#include <iostream>
#include <string>
#include <unordered_map>

namespace samplns {

class CDSIP {
public:
  CDSIP(const TransactionGraph &graph, bool verbose = true)
      : graph(graph), verbose(verbose) {
    env.set(GRB_IntParam_OutputFlag, this->verbose);
    env.start();
  }

  int status() { return grb_status; }

  std::vector<feature_pair>
  solve(const std::vector<feature_pair> &edge_subgraph,
        double timelimit = INFINITY,
        const std::vector<feature_pair> &initial_solution = {}) {
    if (timelimit <= 0.0) {
      return initial_solution;
    }
    try {
      // measure model building time
      auto tstart = std::chrono::steady_clock::now();

      // prepare needed data structures
      const auto nodes = graph.unique_nodes_from_edgelist(edge_subgraph);
      const auto &edges = edge_subgraph;

      // Create an empty model
      GRBModel model = GRBModel(env);

      // Set parameters
      model.set(GRB_IntParam_OutputFlag, this->verbose);

      // Create boolean variable for every edge and weight it with 1.0 for
      // objective
      std::unordered_map<feature_pair, GRBVar> edge_vars;
      for (const auto &e : edges) {
        const auto &[p, q] = e;
        std::string vname = fmt::format("edgevar_{0}_{1}", p, q);
        GRBVar v = model.addVar(0.0, 1.0, 1.0, GRB_BINARY, vname);
        edge_vars[{p, q}] = v;
        edge_vars[{q, p}] = v;
        if (initial_solution.size() > 0) {
          bool activated =
              std::find(initial_solution.cbegin(), initial_solution.cend(),
                        e) != initial_solution.cend();
          v.set(GRB_DoubleAttr_Start, static_cast<double>(activated));
        }
      }

      // edge constraints [parallel edges]
      for (size_t i = 0; i < edges.size(); i++) {
        const auto &[p, q] = edges[i];

        for (size_t j = i + 1; j < edges.size(); j++) {
          const auto &[u, v] = edges[j];
          const bool edges_disjoint = p != u && p != v && q != u && q != v;
          if (edges_disjoint) {
            int edge_sum = graph.has_edge(p, v) + graph.has_edge(q, u) +
                           graph.has_edge(p, u) + graph.has_edge(q, v);
            if (edge_sum == 4) {
              // p, q, u, v form clique -> only one can be selected
              model.addConstr(edge_vars[{p, q}] + edge_vars[{u, v}] <= 1);
            }
          }
        }
      }

      // node constraints [triangle]
      for (feature_id p : nodes) {
        auto neighbors = graph.get_neighbors(p, edges);
        std::sort(neighbors.begin(), neighbors.end());

        for (size_t i = 0; i < neighbors.size(); i++) {
          auto u = neighbors[i];
          for (size_t j = i + 1; j < neighbors.size(); j++) {
            auto v = neighbors[j];
            if (graph.has_edge(u, v)) {
              // p, u, v form clique -> only one edge can be selected
              model.addConstr(edge_vars[{p, u}] + edge_vars[{p, v}] <= 1);
            }
          }
        }
      }

      if (!isinf(timelimit)) {
        auto tstop = std::chrono::steady_clock::now();
        double dt = std::chrono::duration_cast<std::chrono::milliseconds>(
                        tstop - tstart)
                        .count() /
                    1000.0;
        // std::cout << "Building the model took " << dt << " seconds." <<
        // std::endl;
        auto timelimit_ = timelimit - dt;
        if (timelimit_<=0) {
          // Out of time
          return initial_solution;
        }
        model.set(GRB_DoubleParam_TimeLimit, timelimit_);
      }

      // Optimize model
      model.set(GRB_IntAttr_ModelSense, GRB_MAXIMIZE);
      model.optimize();

      grb_status = model.get(GRB_IntAttr_Status);

      if (model.get(GRB_IntAttr_SolCount) > 0) {
        // extract and return IP solution
        std::vector<feature_pair> solution;
        for (const auto &e : edges) {
          auto val = edge_vars[e].get(GRB_DoubleAttr_X);

          if (val > 0.9) {
            solution.push_back(e);
          }
        }
        return solution;
      }

      return std::vector<feature_pair>();
    } catch (GRBException &e) {
      std::cerr << "Error in CDS IP solver (Gurobi):" << std::endl;
      std::cerr << "Error code = " << e.getErrorCode() << std::endl;
      std::cerr << e.getMessage() << std::endl;
      throw e;
    }
  }

private:
  GRBEnv env = GRBEnv(true);
  int grb_status;
  const TransactionGraph &graph;
  const bool verbose;
};
} // namespace samplns

#endif
