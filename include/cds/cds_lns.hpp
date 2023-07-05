#ifndef ALG_SCP_CDS_LNS_HPP
#define ALG_SCP_CDS_LNS_HPP

#include <algorithm>
#include <iomanip>
#include <iostream>
#include <memory>
#include <random>
#include <unordered_set>
#include <vector>

#include "../graph.hpp"
#include "../instance.hpp"
#include "../lns.hpp"
#include "cds_ip.hpp"
#include "cds_operations.hpp"

namespace samplns {

class CDSNeighborhoodSelector
    : public NeighborhoodSelector<TransactionGraph, std::vector<feature_pair>> {
public:
  CDSNeighborhoodSelector(const TransactionGraph &graph,
                          const std::vector<feature_pair> &initial_solution,
                          const std::vector<feature_pair> &subgraph,
                          bool be_smart = true)
      : NeighborhoodSelector(graph), best_solution(initial_solution),
        subgraph(subgraph), be_smart(be_smart) {

    // subgraph validity check
    for (const auto &[p, q] : subgraph) {
      if (!graph.has_edge(p, q)) {
        throw std::runtime_error("The subgraph contains edges that are not "
                                 "present in the transaction graph!");
      }
    }

    // solution contained in subgraph check
    if (subgraph.size() > 0) {
      for (const auto &[p, q] : initial_solution) {
        bool contained = false;
        for (const auto &[u, v] : subgraph) {
          if ((p == u && q == v) || (p == v && q == u)) {
            contained = true;
            break;
          }
        }
        if (!contained) {
          throw std::runtime_error(
              "The inital solutions contains edges that are not "
              "present in the given subgraph!");
        }
      }
    }
  }

  void feedback(Neighborhood<std::vector<feature_pair>> &neighborhood,
                const std::vector<feature_pair> &solution,
                double time_utilization, double nb_utilization) override {

    this->add_solution_to_pool(solution);

    // std::cout << "Utilized " << std::fixed << std::setprecision(2)
    //           << time_utilization * 100.0 << "% of the CDS-LNS iteration
    //           time."
    //           << std::endl;
    if (time_utilization < 0.5) {
      // std::cout << "Increasing neighborhood size from " << max_free_edges;
      max_free_edges += max_free_edges / 10;
      // std::cout << " to " << max_free_edges << "." << std::endl;
    } else if (time_utilization > 0.95) {
      // std::cout << "Decreasing neighborhood size from " << max_free_edges;
      max_free_edges -= max_free_edges / 10;
      max_free_edges = std::max(max_free_edges, FREE_EDGES_LOW_CAP);
      // std::cout << " to " << max_free_edges << "." << std::endl;
    }

    if (time_utilization >= 0.1 && nb_utilization >= 0.5) {
      // std::cout << "Used more than 50% of the time for nbhd "
      //              "construction. Increasing the number of edges added per "
      //              "iteration to ";
      edges_to_add_seq++;
      // std::cout << edges_to_add_seq << "." << std::endl;
    }

    stagnation_counter++;
  }

  /// @brief Lets the neighborhood selector know about a new, better solution.
  /// @param solution The better solution.
  void
  better_solution_callback(const std::vector<feature_pair> &solution) override {
    this->edges_to_add_seq =
        std::max(this->edges_to_add_seq, (solution.size() / 100));
    // std::cout << "edges_to_add_seq = " << this->edges_to_add_seq <<
    // std::endl;
    this->best_solution = solution;
    stagnation_counter = 0;
  }

  Neighborhood<std::vector<feature_pair>> next() override {

    // check if max_free_edges is big enough to cover whole graph/subgraph
    if (!subgraph.empty() && max_free_edges >= subgraph.size()) {
      return {std::vector<feature_pair>(), subgraph};
    } else if (max_free_edges >= graph.count_edges()) {
      return {std::vector<feature_pair>(), graph.get_all_edges()};
    }

    std::vector<feature_pair> initial_solution;

    if (stagnation_counter < STAGNATION_THRESHOLD) {
      // copy best known solution
      initial_solution = this->best_solution;
    } else {
      // choose solution by chance
      initial_solution = solution_pool[std::rand() % solution_pool.size()];

      // std::cout << "Stagnation detected: Using pool solution with "
      //           << initial_solution.size() << " edges." << std::endl;
    }

    // shuffle for higher randomness
    std::shuffle(initial_solution.begin(), initial_solution.end(), rng());

    std::vector<feature_pair> fixed_edges;
    std::vector<feature_pair> remaining_edges;

    if (subgraph.empty()) {
      // select random edge as first fixed edge, calc remaining edges
      fixed_edges.push_back(initial_solution.back());
      initial_solution.pop_back();
      remaining_edges = graph.get_edges([&](const feature_pair &edge) {
        return this->is_remaining_edge(edge, fixed_edges);
      });
    } else {
      // only consider subgraph
      remaining_edges = subgraph;
    }

    std::vector<feature_pair> remaining_edges_cpy = remaining_edges;
    size_t edges_added_in_iter = 0;

    // iteratively select next random edge, update remaining edges in place
    while (!initial_solution.empty() &&
           remaining_edges.size() > max_free_edges) {
      remaining_edges_cpy = remaining_edges;
      edges_added_in_iter = 0;
      for (size_t i = 0; i < edges_to_add_seq && !initial_solution.empty();
           i++) {
        fixed_edges.push_back(initial_solution.back());
        initial_solution.pop_back();
        edges_added_in_iter++;
      }
      update_remaining_edges(fixed_edges, remaining_edges);
    }

    // Restore penultimate step if all edges were eliminated
    if (remaining_edges.empty()) {
      // std::cout << "Erased all edges. Restoring "
      //              "penultimate state."
      //           << std::endl;
      for (size_t i = 0; i < edges_added_in_iter; i++) {
        initial_solution.push_back(fixed_edges.back());
        fixed_edges.pop_back();
      }
      remaining_edges = remaining_edges_cpy;
    }

    // erase random edges if remaining_edges are still too many
    if (remaining_edges.size() > max_free_edges) {
      // std::cout << "Randomly erased "
      //           << remaining_edges.size() - max_free_edges;

      // erase all edges from initial_solution from remaining_edges
      if (initial_solution.size() > 0) {
        auto new_end =
            std::remove_if(remaining_edges.begin(), remaining_edges.end(),
                           [&](const feature_pair &e) {
                             auto itr = std::find(initial_solution.cbegin(),
                                                  initial_solution.cend(), e);
                             return itr != initial_solution.cend();
                           });
        size_t new_len = std::distance(remaining_edges.begin(), new_end);
        if (new_len != remaining_edges.size() - initial_solution.size()) {
          throw std::runtime_error(
              "Some edges from the initial solution were not part of the "
              "remaining edges! (symmetry inconsistencies?)");
        }
        remaining_edges.resize(new_len);
      }

      // erase random edges, reappend initial solution edges
      std::shuffle(remaining_edges.begin(), remaining_edges.end(), rng());
      remaining_edges.resize(max_free_edges - initial_solution.size());
      remaining_edges.insert(remaining_edges.end(), initial_solution.cbegin(),
                             initial_solution.cend());
      // std::cout << " edges." << std::endl;
    }

    // std::cout << "CDS neighborhood has " << remaining_edges.size()
    //           << " free edges." << std::endl;

    return {fixed_edges, remaining_edges};
  }

private:
  void add_solution_to_pool(const std::vector<feature_pair> &solution) {

    for (const auto &sol : solution_pool) {
      if (sol == solution) {
        return;
      }
    }

    solution_pool.push_back(solution);

    // sort solutions by length (descending)
    std::sort(solution_pool.begin(), solution_pool.end(),
              [&](const std::vector<feature_pair> &sol1,
                  const std::vector<feature_pair> &sol2) {
                return sol1.size() > sol2.size();
              });

    if (solution_pool.size() > SOLUTION_POOL_SIZE) {
      solution_pool.resize(SOLUTION_POOL_SIZE);
    }
  }

  void update_remaining_edges(const std::vector<feature_pair> &fixed_edges,
                              std::vector<feature_pair> &remaining_edges) {
    // (efficiently) remove all elements from list of remaining edges that are
    // not feasible anymore
    auto it =
        std::remove_if(remaining_edges.begin(), remaining_edges.end(),
                       [&](const feature_pair &edge) {
                         return !this->is_remaining_edge(edge, fixed_edges);
                       });
    remaining_edges.resize(std::distance(remaining_edges.begin(), it));
  }

  [[nodiscard]] inline bool
  is_remaining_edge(const feature_pair &edge,
                    const std::vector<feature_pair> &fixed_edges) const {
    return std::all_of(fixed_edges.cbegin(), fixed_edges.cend(),
                       [&edge, this](const auto &o_edge) {
                         return this->graph.are_edges_clique_disjoint(edge,
                                                                      o_edge);
                       });
  }

  const size_t FREE_EDGES_LOW_CAP = 250;
  const size_t STAGNATION_THRESHOLD = 5;
  const size_t SOLUTION_POOL_SIZE = STAGNATION_THRESHOLD * 4;

  size_t edges_to_add_seq = 1;
  size_t stagnation_counter = 0;
  size_t max_free_edges = 1000;
  std::vector<feature_pair> best_solution;
  std::vector<std::vector<feature_pair>> solution_pool;

  const TransactionGraph &graph = instance;
  const std::vector<feature_pair> subgraph;
  const bool be_smart; // toggle for experiments
};

class CDSSolver
    : public LowerBoundLNS<TransactionGraph, std::vector<feature_pair>> {
public:
  CDSSolver(const TransactionGraph &graph,
            const std::vector<feature_pair> &initial_solution,
            const std::vector<feature_pair> &subgraph = {},
            bool nbhd_selector_be_smart = true)
      : LowerBoundLNS(new CDSNeighborhoodSelector(graph, initial_solution,
                                                  subgraph,
                                                  nbhd_selector_be_smart),
                      initial_solution),
        graph(graph), be_smart(nbhd_selector_be_smart) {}

  [[nodiscard]] int64_t
  get_solution_score(const std::vector<feature_pair> &solution) const override {
    return (int64_t)solution.size();
  }

  [[nodiscard]] bool is_optimal_solution(
      const std::vector<feature_pair> &solution) const override {
    return this->proven_optimal;
  }

  std::vector<feature_pair>
  optimize_neighborhood(Neighborhood<std::vector<feature_pair>> &neighborhood,
                        double timelimit) override {

    const auto &edge_subgraph = neighborhood.free_solution;
    set_iteration_statistic("nbhd_fixed_size",
                            neighborhood.fixed_solution.size());
    set_iteration_statistic("nbhd_free_size",
                            neighborhood.free_solution.size());

    // add hints to model
    std::vector<feature_pair> hints;
    // if (be_smart) {
    //   const auto &best_sol = get_best_solution();
    //   hints = neighborhood.free_solution;
    //   auto it = std::remove_if(hints.begin(), hints.end(), [&](feature_pair
    //   e) {
    //     return std::find(best_sol.cbegin(), best_sol.cend(), e) ==
    //            best_sol.cend();
    //   });

    //   hints.erase(it, hints.end());
    //   std::cout << hints.size() << " tuples in initial hint solution."
    //             << std::endl;
    // }

    // solve ip
    auto solution = ip_model.solve(edge_subgraph, timelimit, hints);
    if (solution.empty()) {
      return neighborhood.fixed_solution;
    }

    set_iteration_statistic("grb_status", ip_model.status());

    // check validity of solution (debugging)
    cds_check_solution(graph, solution);

    // check optimality
    if (neighborhood.fixed_solution.empty()) {
      proven_optimal |= (ip_model.status() == GRB_OPTIMAL);
    }
    set_iteration_statistic("proven_optimal",
                            static_cast<int64_t>(proven_optimal));

    // copy fixed part to solution
    solution.reserve(solution.size() + neighborhood.fixed_solution.size());
    solution.insert(solution.end(), neighborhood.fixed_solution.begin(),
                    neighborhood.fixed_solution.end());

    set_iteration_statistic("found_solution_size", solution.size());
    set_iteration_statistic(
        "global_lb", std::max(solution.size(), get_best_solution().size()));

    return solution;
  }

private:
  bool proven_optimal = false;

  const TransactionGraph &graph;
  CDSIP ip_model = CDSIP(graph, false); // not verbose
  const bool be_smart;
};
} // namespace samplns

#endif
