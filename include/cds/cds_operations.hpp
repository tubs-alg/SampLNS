#ifndef ALG_SCP_CDS_OPERATIONS_HPP
#define ALG_SCP_CDS_OPERATIONS_HPP

#include "../graph.hpp"
#include "../instance.hpp"

namespace samplns {
// static cds_join(const TransactionGraph& graph, const
// std::vector<feature_pair>& source, std::vector<feature_pair>& destination)
// {
//     std::vector<feature_pair> added_edges;
//     destination.reserve(destination.size() + source.size());

//     for (const auto& new_edge : source)
//     {
//         bool to_add = true;
//         for (const auto& old_edge : destination)
//         {
//             if (!graph.are_edges_clique_disjoint(new_edge, old_edge))
//             {
//                 to_add = false;
//                 break;
//             }
//         }

//         if (to_add)
//         {
//             added_edges.push_back(new_edge);
//         }
//     }
// }

static void cds_check_solution(const TransactionGraph &graph,
                               const std::vector<feature_pair> &solution) {
  if (!graph.are_edges_clique_disjoint(solution)) {
    std::cout << "ERROR: The solution returned by CDSSolver is invalid! (Not "
                 "disjoint)"
              << std::endl;
    throw std::runtime_error(
        "The solution returned by CDSSolver is invalid! (Not disjoint)");
  }
  for (const auto &[p, q] : solution) {
    if (!graph.has_edge(p, q)) {
      std::cout << "ERROR: The solution contains edges that are not part of "
                   "the graph!"
                << std::endl;
      throw std::runtime_error(
          "The solution contains edges that are not part of the graph!");
    }
  }
  for (size_t i = 0; i < solution.size(); i++) {
    for (size_t j = i + 1; j < solution.size(); j++) {
      const auto &[p, q] = solution[i];
      const auto &[u, v] = solution[j];
      if ((p == u && q == v) || (p == v && q == u)) {
        std::cout << "ERROR: The solution contains non-unique edges!"
                  << std::endl;
        throw std::runtime_error("The solution contains non-unique edges!");
      }
    }
  }
}
} // namespace samplns

#endif
