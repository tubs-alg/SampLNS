#ifndef ALG_SCP_CDS_GREEDY_HPP
#define ALG_SCP_CDS_GREEDY_HPP

#include "../graph.hpp"
#include "../instance.hpp"
#include "cds_operations.hpp"

#include <unordered_map>
#include <vector>

// namespace samplns {

class CounterMatrix {
public:
  CounterMatrix(size_t n) : size_(n), data_(gauss(n), 0) {}

  inline uint32_t get(feature_id i, feature_id j) const {
    return data_[index(i, j)];
  }

  inline void set(feature_id i, feature_id j, uint32_t value) {
    data_[index(i, j)] = value;
  }

  inline void increment(feature_id i, feature_id j, uint32_t value) {
    data_[index(i, j)] += value;
  }

  inline size_t size() const { return size_; }

private:
  inline size_t index(feature_id x, feature_id y) const {

    size_t i = lit_to_index(x);
    size_t j = lit_to_index(y);

    if (i == j)
      throw std::runtime_error(
          "Error: Call to CounterMatrix::index with identical node indeces! "
          "(Edge from node to itself does not exist!)");
    if (i > j)
      std::swap(i, j);
    return i * size_ - (i * (i + 1)) / 2 + j;
  }

  inline size_t lit_to_index(feature_id lit) const {
    bool is_pos = lit > 0;
    return (size_t)(lit + size_ / 2 - is_pos);
  }

  size_t size_;
  std::vector<uint32_t> data_;
};

class IndependentSet {
public:
  IndependentSet(const TransactionGraph &graph) : graph(graph) {}

  void add_if_independent(const feature_pair &e) {
    if (is_independent(e)) {
      add(e);
    }
  }

  bool is_independent(const feature_pair &e) {
    for (const auto &f : solution) {
      if (!graph.are_edges_clique_disjoint(e, f)) {
        return false;
      }
    }
    return true;
  }

  const std::vector<feature_pair> get() { return solution; }

private:
  void add(const feature_pair &e) { solution.push_back(e); }

  const TransactionGraph &graph;
  std::vector<feature_pair> solution;
};

class GreedyCDS {
public:
  GreedyCDS(const TransactionGraph &graph,
            std::vector<std::vector<feature_id>> sample)
      : graph(graph), cover_counters(graph.count_nodes()) {
    do_sort = sample.size() > 0;
    //std::cout << "GREEDY CDS: Using " << sample.size()
    //          << " configurations to count covering." << std::endl;

    // count how many times feature pairs are covered
    for (const auto &configuration : sample) {
      for (size_t i = 0; i < configuration.size(); i++) {
        for (size_t j = i + 1; j < configuration.size(); j++) {
          cover_counters.increment(configuration[i], configuration[j], 1);
        }
      }
    }
  }

  std::vector<feature_pair>
  optimize(const std::vector<feature_pair> &subgraph) {

    std::vector<feature_pair> feasible_tuples;
    if (subgraph.empty()) {
      feasible_tuples = graph.get_all_edges();
    } else {
      feasible_tuples = subgraph;
    }

   // std::cout << "GREEDY CDS: considering " << feasible_tuples.size()
    //          << " tuples!" << std::endl;

    // sort tuples ascending by cover counters
    std::shuffle(feasible_tuples.begin(), feasible_tuples.end(), rng());
    std::cout << "GREEDY CDS: Shuffling done." << std::endl;
    if (do_sort) {
      std::stable_sort(feasible_tuples.begin(), feasible_tuples.end(),
                       [&](const feature_pair &a, const feature_pair b) {
                         const auto &[p, q] = a;
                         const auto &[u, v] = b;
                         return cover_counters.get(p, q) <
                                cover_counters.get(u, v);
                       });
      //std::cout << "GREEDY CDS: Sorting done." << std::endl;
    } else {
      //std::cout << "GREEDY CDS: Sorting skipped." << std::endl;
    }

    // construct cds
    IndependentSet cds(graph);
    for (const auto &e : feasible_tuples) {
      cds.add_if_independent(e);
    }

    const auto &solution = cds.get();

    cds_check_solution(graph, solution);

   // std::cout << "GREEDY CDS: Found CDS of size " << solution.size() << "."
    //          << std::endl;

    return solution;
  }

private:
  bool do_sort;
  const TransactionGraph &graph;
  CounterMatrix cover_counters;
};

#endif
