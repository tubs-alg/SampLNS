#ifndef ALG_SCP_CDS_HEURISTIC_HPP
#define ALG_SCP_CDS_HEURISTIC_HPP

#include "../graph.hpp"
#include "../instance.hpp"
#include "../lns.hpp"
#include "../mis/mis_ip.hpp"
#include <chrono>
#include <random>
#include <unordered_map>
#include <vector>

namespace samplns {

static inline std::vector<feature_pair>
local_neighborhood_cds(const TransactionGraph &graph, feature_id node = 1) {
  const auto neighbors = graph.get_neighbors(node);

  auto selected_neighbors = MISIP(graph).solve(neighbors);
  selected_neighbors.push_back(node);

  const auto cds = graph.induced_subgraph_edges(selected_neighbors);

  if (!graph.are_edges_clique_disjoint(cds)) {
    json jcds = cds;
    throw std::runtime_error(
        "The local CDS found by a MISIP is not disjoint! " + jcds.dump());
  }

  return cds;
}

static inline std::vector<feature_pair> local_neighborhood_cds(
    const TransactionGraph &graph, feature_id node,
    std::unordered_map<feature_id, std::vector<feature_pair>> &cache) {
  if (cache.count(node)) {
    return cache[node];
  }

  return cache[node] = local_neighborhood_cds(graph, node);
}

class MISNodeSelector
    : public NeighborhoodSelector<TransactionGraph, std::vector<feature_pair>> {
public:
  MISNodeSelector(const TransactionGraph &graph)
      : NeighborhoodSelector(graph) {}

  Neighborhood<std::vector<feature_pair>> next() override {
    if (std::rand() % 100 < 70) {
      clear_solution();
    } else {
      clear_high_collision_rate_edges();
    }
    return neighborhood;
  }

  /// @brief Empty the current cds.
  void clear_solution() {
    neighborhood.fixed_solution.clear();
    collision_counters.clear();
    std::cout << "Cleared CDS!" << std::endl;
  }

  /// @brief Sort the current cds solution in an ascending order and cut off the
  /// last n elements.
  void clear_high_collision_rate_edges() {
    auto &current_cds = neighborhood.fixed_solution;

    std::sort(current_cds.begin(), current_cds.end(),
              [&](const feature_pair &e1, const feature_pair &e2) {
                return count_collisions(e1) < count_collisions(e2);
              });

    for (size_t i = current_cds.size() / 2; i < current_cds.size(); i++) {
      reset_collisions(current_cds[i]);
    }

    std::cout << "Resized CDS from " << current_cds.size();
    current_cds.resize(current_cds.size() / 2);
    std::cout << " to " << current_cds.size() << " edges!" << std::endl;
  }

  void feedback(Neighborhood<std::vector<feature_pair>> &neighborhood,
                const std::vector<feature_pair> &solution,
                double time_utilization, double nb_utilization) override {
    if (solution.size() > this->neighborhood.fixed_solution.size()) {
      this->neighborhood.fixed_solution = solution;
    }
  }

  /// @brief Increase the collision counter of the given edge by one (or set it
  /// to 1, if did not exist).
  /// @param edge the edge to report the collision on.
  void report_collision(feature_pair edge) {
    if (edge.first > edge.second) {
      std::swap(edge.first, edge.second);
    }
    auto [it, was_inserted] = collision_counters.try_emplace(edge, 1);
    it->second += !was_inserted; // if element is not new, add 1
  }

private:
  uint32_t count_collisions(feature_pair edge) const {
    if (edge.first > edge.second) {
      std::swap(edge.first, edge.second);
    }

    auto it = collision_counters.find(edge);
    if (it == collision_counters.end()) {
      return 0;
    } else {
      return it->second;
    }
  }

  void reset_collisions(feature_pair edge) {
    if (edge.first > edge.second) {
      std::swap(edge.first, edge.second);
    }
    collision_counters.erase(edge);
  }

  int iterations = 0;
  Neighborhood<std::vector<feature_pair>> neighborhood;
  std::unordered_map<feature_pair, uint32_t>
      collision_counters; // used to identify edges causing many collisions
};

class CDSNodeHeuristic
    : public LowerBoundLNS<TransactionGraph, std::vector<feature_pair>> {
public:
  CDSNodeHeuristic(const TransactionGraph &graph,
                   const std::vector<feature_pair> &initial_solution)
      : LowerBoundLNS(nb_selector = new MISNodeSelector(graph),
                      initial_solution),
        graph(graph), misip_solver(graph) {
    std::cout << "Graph has " << graph.count_nodes() << " nodes." << std::endl;
  }

  std::vector<feature_pair>
  optimize_neighborhood(Neighborhood<std::vector<feature_pair>> &neighborhood,
                        double timelimit) override {

    bool restart = neighborhood.fixed_solution.empty();
    auto &current_cds = neighborhood.fixed_solution;
    std::cout << "Starting with CDS of size " << current_cds.size() << "."
              << std::endl;

    std::random_device rd;
    std::mt19937 random_generator(rd());

    const double tstart = timestamp();

    auto time_passed = [&]() {
      const double tstop = timestamp();
      return (tstop - tstart) / 1000.0;
    };

    if (restart) {
      update_cliques();
    }

    size_t nodes_optimized = 0;

    // start at largest clique, optimize, move to smaller cliques
    for (auto &clique : cliques) {
      if (time_passed() >= timelimit)
        break;

      // shuffle clique, move cached CDS solutions to front

      std::shuffle(clique.begin(), clique.end(), random_generator);
      std::stable_sort(clique.begin(), clique.end(),
                       [&](const feature_id &i, const feature_id &j) {
                         return cached_node_cds.count(i) >
                                cached_node_cds.count(j);
                       });

      for (size_t i = 0; i < clique.size() && time_passed() < timelimit; i++) {
        const feature_id node = clique[i];

        // Solve maximum independent set around node to optimality
        const auto max_indep_set =
            local_neighborhood_cds(graph, node, cached_node_cds);
        nodes_optimized++;

        // Merge into current best solution
        add_edges_to_global_cds(max_indep_set, current_cds);
      }
    }

    // try to add edges from best solution to current
    if (nodes_optimized >= 2) {
      add_edges_to_global_cds(this->get_best_solution(), current_cds);
    }

    std::cout << "Optimized and merged " << nodes_optimized << " local CDS."
              << std::endl;
    // std::cout << cached_node_cds.size() << " local CDS are cached." <<
    // std::endl;

    return current_cds;
  }

  size_t add_edges_to_global_cds(const std::vector<feature_pair> &edges,
                                 std::vector<feature_pair> &current_cds) {
    std::vector<feature_pair> added_edges;

    current_cds.reserve(current_cds.size() + edges.size());
    uint64_t total_conflicts = 0;

    for (const auto &new_edge : edges) {
      bool add_edge = true;
      for (const auto &existing_edge : current_cds) {
        if (!graph.are_edges_clique_disjoint(new_edge, existing_edge)) {
          nb_selector->report_collision(existing_edge);
          add_edge = false;
          total_conflicts++;
        }
      }
      if (add_edge) {
        added_edges.push_back(new_edge);
      }
    }

    if (added_edges.size() > 0) {
      current_cds.insert(current_cds.end(), added_edges.begin(),
                         added_edges.end());
      std::cout << "CDS size was increased to " << current_cds.size() << ". ("
                << total_conflicts << " total conflicts)" << std::endl;
    }

    if (!graph.are_edges_clique_disjoint(current_cds)) {
      std::runtime_error(
          "Current cds became non-disjoint after add_edges_to_global_cds!");
    }

    return added_edges.size();
  }

  int64_t
  get_solution_score(const std::vector<feature_pair> &edges) const override {
    return edges.size();
  }

  void update_cliques() {
    auto maximal_cliques = graph.complement_clique_heuristic();

    size_t s_og = 0;
    for (const auto &clique : cliques) {
      s_og = std::max(s_og, clique.size());
    }

    size_t s_new = 0;
    for (const auto &clique : maximal_cliques) {
      s_new = std::max(s_new, clique.size());
    }

    if (s_new > s_og) {
      cliques = maximal_cliques;

      std::cout << "Updated set of cliques! Largest one has size " << s_new
                << std::endl;
    }
  }

private:
  const TransactionGraph &graph;
  const MISIP misip_solver;

  MISNodeSelector *nb_selector;
  std::unordered_map<feature_id, std::vector<feature_pair>> cached_node_cds;
  std::vector<std::vector<feature_id>> cliques;
};
} // namespace samplns

#endif
