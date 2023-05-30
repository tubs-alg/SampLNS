#ifndef ALG_SCP_MIS_IP_HPP
#define ALG_SCP_MIS_IP_HPP

#include "../graph.hpp"
#include "../instance.hpp"
#include "gurobi_c++.h"
#include <algorithm>
#include <fmt/core.h>
#include <iostream>
#include <string>
#include <unordered_map>

namespace samplns {

class MISIP {
public:
  MISIP(const TransactionGraph &graph, bool verbose = false)
      : graph(graph), verbose(verbose) {
    env.set(GRB_IntParam_OutputFlag, this->verbose);
    env.start();
  }

  std::vector<feature_id> solve(const std::vector<feature_id> &nodes,
                                double timelimit = INFINITY) {

    // Create an empty model
    GRBModel model = GRBModel(env);

    // Set parameters
    model.set(GRB_IntParam_OutputFlag, this->verbose);

    // Create boolean variable for every vertex and weight it with 1.0 for
    // objective
    std::unordered_map<feature_id, GRBVar> vars;
    for (const auto &p : nodes) {
      std::string vname = fmt::format("var_{}", p);
      GRBVar v = model.addVar(0.0, 1.0, 1.0, GRB_BINARY, vname);
      vars[p] = v;
    }

    // edge constraints
    for (const auto &[p, q] : graph.induced_subgraph_edges(nodes)) {
      model.addConstr(vars[p] + vars[q] <= 1.0);
    }

    // Optimize model
    model.set(GRB_IntAttr_ModelSense, GRB_MAXIMIZE);
    model.optimize();

    // extract solution
    std::vector<feature_id> selected_nodes;
    for (const auto &p : nodes) {
      if (vars[p].get(GRB_DoubleAttr_X) > 0.9) {
        selected_nodes.push_back(p);
      }
    }

    return selected_nodes;
  }

private:
  GRBEnv env = GRBEnv(true);
  const TransactionGraph &graph;
  const bool verbose;
};
} // namespace samplns

#endif
