#ifndef ALG_SCP_CDS_GENETIC_HPP
#define ALG_SCP_CDS_GENETIC_HPP

#include <algorithm>
#include <cmath>
#include <random>
#include <vector>

#include "../graph.hpp"
#include "../instance.hpp"
#include "cds_heuristic.hpp"

namespace samplns {

static double roll() {
  static std::random_device rd;
  static std::mt19937 gen(rd());
  static std::uniform_real_distribution<> dis(0.0, 1.0);

  return dis(gen);
}

class GeneticCDS {
public:
  GeneticCDS(const TransactionGraph &graph, size_t max_creatures)
      : graph(graph), max_creatures(max_creatures) {
    std::cout << "Generating creatures..." << std::endl;
    creatures.reserve(max_creatures);

    // insert some local optimal creatures
    const size_t n =
        std::min(std::min((size_t)5, max_creatures), graph.count_nodes());
    for (size_t i = 0; i < n; i++) {
      const feature_id index = ((i / 2) + 1) * (i % 2 ? -1 : 1);
      creatures.push_back(local_neighborhood_cds(graph, index));
    }

    update_best();

    // fill with greedily generated creatures
    while (creatures.size() < max_creatures) {
      creatures.push_back(generate_creature());
    }

    std::cout << "Done!" << std::endl;

    update_best();
  }

  /// @brief Generate a "new" creature, based on taking edges from best known
  /// species and constructing rest greedily
  /// @return A new creature
  std::vector<feature_pair> generate_creature() {
    const auto &best = get_best_solution();
    const auto start_edge = best[std::rand() % best.size()];

    std::vector<feature_pair> creature = {start_edge};
    std::vector<feature_pair> remaining_edges =
        graph.get_edges([&](const feature_pair &edge) {
          for (const auto &o_edge : creature) {
            if (!this->graph.are_edges_clique_disjoint(edge, o_edge)) {
              return false;
            }
          }
          return true;
        });

    for (const auto &edge : remaining_edges) {
      bool add = true;
      for (const auto &o_edge : creature) {
        if (!this->graph.are_edges_clique_disjoint(edge, o_edge)) {
          add = false;
          break;
        }
      }
      if (add) {
        creature.push_back(edge);
      }
    }

    return creature;
  }

  std::vector<feature_pair> &get_fit_creature() {
    // the chance should be 50% to exceed top 10%
    const double p = std::pow(0.5, 1.0 / (max_creatures * 0.10));
    std::cout << roll() << std::endl;

    // calculate index of breeding creature
    size_t i = 0;
    for (; i < max_creatures - 1; i++) {
      if (p > roll()) {
        break;
      }
    }

    return creatures[i];
  }

  void optimize(size_t iterations) {
    for (size_t itr = 0; itr < iterations; itr++) {
      // breeding phase: sort creatures, replace bottom half by breeding
      // creatures based on their fitness

      std::sort(creatures.begin(), creatures.end(),
                [](const std::vector<feature_pair> &a,
                   const std::vector<feature_pair> &b) {
                  return a.size() < b.size();
                });

      for (size_t i = max_creatures / 2; i < max_creatures; i++) {
        creatures[i] = breed(get_fit_creature(), get_fit_creature());
      }

      update_best();

      // mutation phase

      for (auto &creature : creatures) {
        if (roll() < mutation_rate) {
          mutate(creature);
        }
      }

      update_best();
    }
  }

  void update_best() {
    for (const auto &creature : creatures) {
      if (creature.size() > best_creature.size()) {
        best_creature = creature;
        return;
      }
    }
  }

  std::vector<feature_pair> breed(const std::vector<feature_pair> &v1,
                                  const std::vector<feature_pair> &v2) {
    // copy one parent's genome
    std::vector<feature_pair> new_creature = v1;

    // copy all fitting edges from other parent
    for (const auto &new_edge : v2) {
      for (const auto &existing_edge : new_creature) {
        if (!graph.are_edges_clique_disjoint(new_edge, existing_edge)) {
          break;
        }
      }
      new_creature.push_back(new_edge);
    }

    return new_creature;
  }

  void mutate(std::vector<feature_pair> &creature) {
    // remove 50% of edges
    std::shuffle(creature.begin(), creature.end(), rng());
    creature.resize(creature.size() / 2);
  }

  const std::vector<feature_pair> &get_best_solution() { return best_creature; }

private:
  std::vector<std::vector<feature_pair>> creatures;
  std::vector<feature_pair> best_creature;
  const TransactionGraph &graph;
  const size_t max_creatures;
  const double mutation_rate = 0.33;
};

} // namespace samplns

#endif
