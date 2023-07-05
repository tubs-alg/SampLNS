#ifndef ALG_SCP_GRAPH_HPP
#define ALG_SCP_GRAPH_HPP

#include "instance.hpp"

#include <algorithm>
#include <fmt/core.h>
#include <functional>
#include <iostream>
#include <math.h>
#include <random>
#include <stdint.h>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

namespace samplns {

static constexpr size_t gauss(size_t n) { return n * (n + 1) / 2; };

/// @brief An adjacency matrix in lower triangular form. Its main goal
/// is to achieve high memory efficiency and low access times because
/// of a long, continuous stripe of memory
class TriangularMatrix {
public:
  TriangularMatrix(size_t n) : size_(n), data_(gauss(n), false) {}

  inline bool get(size_t i, size_t j) const { return data_[index(i, j)]; }

  inline void set(size_t i, size_t j, bool value) {
    data_[index(i, j)] = value;
  }

  inline void flip() { data_.flip(); }

  inline size_t size() const { return size_; }

private:
  inline size_t index(int i, int j) const {
    if (i == j)
      throw std::runtime_error(
          "Error: Call to TriangularMatrix::index with identical node indeces! "
          "(Edge from node to itself does not exist!)");
    if (i > j)
      std::swap(i, j);
    return i * size_ - (i * (i + 1)) / 2 + j;
  }

  size_t size_;
  std::vector<bool> data_;
};

class TransactionGraph {
public:
  TransactionGraph(uint64_t num_vars)
      : num_vars(num_vars), num_nodes(num_vars * 2),
        num_cells(gauss(num_nodes - 1)), adjacency_matrix(num_nodes) {
    // std::cout << "Transaction graph built." << std::endl;
  }

  /// @brief Returns the number of edges in the graph. Despite it's name, it is
  /// a constant time operation.
  /// @return The number of edges in the graph.
  inline size_t count_edges() const { return this->num_edges; }

  /// @brief Returns the number of nodes in the graph. Despite it's name, it is
  /// a constant time operation.
  /// @return The number of nodes in the graph.
  inline size_t count_nodes() const { return this->num_nodes; }

  /// @brief Tries to add the edge between the given literal nodes (if not
  /// already present)
  /// @param lit1 The first literal node (order does not matter)
  /// @param lit2 The second literal node (order does not matter)
  /// @return True if the edge was not present before and was newly added. False
  /// if the edge was already present.
  inline bool add_edge(feature_id lit1, feature_id lit2) {
    const auto i = lit_to_index(lit1);
    const auto j = lit_to_index(lit2);
    bool edge_added = !this->adjacency_matrix.get(i, j);
    this->num_edges += edge_added;
    this->adjacency_matrix.set(i, j, true);
    return edge_added;
  }

  /// @brief Marks all pairs of features in the configuration as valid.
  /// In other words, adds pairwise edges between all nodes representing
  /// features in the configuration.
  /// @param configuration The configuration.
  void add_valid_configuration(const std::vector<feature_id> &configuration) {
    for (size_t i = 0; i < configuration.size(); i++) {
      for (size_t j = i + 1; j < configuration.size(); j++) {
        this->add_edge(configuration[i], configuration[j]);
      }
    }
  }

  /// @brief Checks if the graph has an edge between the two given literal
  /// nodes.
  /// @param lit1 The first literal node (order does not matter)
  /// @param lit2 The second literal node (order does not matter)
  /// @return True if there is an edge between lit1 and lit2. False otherwise.
  inline bool has_edge(feature_id lit1, feature_id lit2) const {
    const auto i = lit_to_index(lit1);
    const auto j = lit_to_index(lit2);
    return this->adjacency_matrix.get(i, j);
  }

  /// @brief Tries to remove the edge between the given literal nodes (if
  /// present).
  /// @param lit1 The first literal node (order does not matter)
  /// @param lit2 The second literal node (order does not matter)
  /// @return True if the edge was present before and was removed. False if the
  /// edge was not present.
  inline bool remove_edge(feature_id lit1, feature_id lit2) {
    const auto i = lit_to_index(lit1);
    const auto j = lit_to_index(lit2);
    bool edge_removed = this->adjacency_matrix.get(i, j);
    this->num_edges -= edge_removed;
    this->adjacency_matrix.set(i, j, false);
    return edge_removed;
  }

  /// @brief Flips every bit in the adjacency matrix. This causes the graph to
  /// become the complement of itself.
  void complement() { this->adjacency_matrix.flip(); }

  /// @brief For debugging purposes. Exports a "dotgraph" representation of the
  /// graph. This can be used to draw the graph using e.g. graphviz.
  /// @param dest The destination stream.
  void export_dotgraph(std::ostream &dest) const {

    dest << "strict graph {" << std::endl;

    for (feature_id v = -(feature_id)num_vars; v <= (feature_id)num_vars; v++) {
      for (feature_id w = v + 1; w <= (feature_id)num_vars; w++) {
        if (v == w || v == 0 || w == 0)
          continue;

        if (has_edge(v, w)) {
          dest << v << " -- " << w << std::endl;
        }
      }
    }

    dest << "}" << std::endl;
  }

  /// @brief Calculates and returns the list of edges of the subgraph induced by
  /// the given list of nodes.
  /// @param nodes The list of nodes
  /// @return the list of edges.
  std::vector<feature_pair>
  induced_subgraph_edges(const std::vector<feature_id> &nodes) const {
    std::vector<feature_pair> edges;

    for (size_t i = 0; i < nodes.size(); i++) {
      const auto &n1 = nodes[i];
      for (size_t j = i + 1; j < nodes.size(); j++) {
        const auto &n2 = nodes[j];
        if (this->has_edge(n1, n2)) {
          edges.push_back({n1, n2});
        }
      }
    }

    return edges;
  }

  /// @brief Test, whether the LitGraph instance correctly represents the given
  /// instance. (Throws assertions if not)
  /// @param instance The instance to test against.
  void test(const Instance &instance) const {
    assert(this->num_vars == instance.n_concrete);
    assert(this->num_nodes == instance.n_concrete * 2);

    std::unordered_map<feature_id, std::unordered_set<feature_id>> confl_map(
        instance.conflicts.size());

    for (const auto &[p, q] : instance.conflicts) {
      for (auto x : {p, q}) {
        if (confl_map.find(x) == confl_map.end()) {
          confl_map[x] = std::unordered_set<feature_id>();
        }
      }

      assert(!has_edge(p, q));
      assert(!has_edge(q, p));

      confl_map[p].emplace(q);
      confl_map[q].emplace(p);
    }

    for (feature_id i = -(feature_id)this->num_vars;
         i < (feature_id)this->num_vars; i++) {
      for (feature_id j = i + 1; j <= (feature_id)this->num_vars; j++) {
        if (i == 0 || j == 0)
          continue;

        assert(lits_to_indices(i, j) == lits_to_indices(j, i));

        bool i_j_confl = (confl_map[i].find(j) != confl_map[i].end());
        (void)i_j_confl;
        bool j_i_confl = (confl_map[j].find(i) != confl_map[j].end());
        (void)j_i_confl;
        assert(i_j_confl == j_i_confl);

        assert(has_edge(i, j) == has_edge(j, i));
        assert(has_edge(i, j) == !i_j_confl);
      }
    }
  }

  /// @brief Performs a test on the graph implementation which throws exceptions
  /// on failure.
  void test() const {
    size_t edge_count = 0;
    for (feature_id i = (feature_id)-num_vars; i <= (feature_id)num_vars; i++) {
      for (feature_id j = i + 1; j <= (feature_id)num_vars; j++) {
        if (i != 0 && j != 0) {
          if (has_edge(i, j) != has_edge(j, i)) {
            std::runtime_error(fmt::format("Graph Test failed: has_edge not "
                                           "symmetric for edge ({0}, {1})!",
                                           i, j));
          }
          edge_count += has_edge(i, j);
        }
      }
    }
    if (edge_count != num_edges) {
      std::runtime_error(
          fmt::format("Graph Test failed: num_edges not consistent! "
                      "actual amount of edges: {0}. Reported count: {1}!",
                      edge_count, num_edges));
    }
  }

  /// @brief Finds all neighbors adjacent to the given literal node. (This can
  /// be a very large amount, consider using one of the other two "filtered"
  /// methods)
  /// @param lit The literal node.
  /// @return The list of nodes adjacent to the literal node.
  std::vector<feature_id> get_neighbors(feature_id lit) const {
    std::vector<feature_id> neighbors;

    for (feature_id i = -(feature_id)this->num_vars;
         i <= (feature_id)this->num_vars; i++) {
      if (i == lit || i == 0)
        continue;

      if (has_edge(i, lit)) {
        neighbors.push_back(i);
      }
    }

    return neighbors;
  }

  /// @brief Counts the number of nodes adjacent to the given literal node.
  /// @param lit The literal node.
  /// @return The list of nodes adjacent to the literal node.
  size_t count_neighbors(feature_id lit) const {

    size_t cnt = 0;

    for (feature_id i = -(feature_id)this->num_vars;
         i <= (feature_id)this->num_vars; i++) {
      if (i == 0 || i == lit)
        continue;
      cnt += has_edge(i, lit);
    }

    return cnt;
  }

  /// @brief Finds all neighbors of the literal node that are contained in the
  /// given list of nodes (subgraph).
  /// @param lit The literal node.
  /// @param subgraph The nodes to "filter" by.
  /// @return The list of nodes adjacent to the literal node.
  std::vector<feature_id>
  get_neighbors(feature_id lit, const std::vector<feature_id> &subgraph) const {
    std::vector<feature_id> neighbors;
    for (const auto &x : subgraph) {
      if (has_edge(lit, x)) {
        neighbors.push_back(x);
      }
    }
    return neighbors;
  }

  /// @brief Finds all neighbors of the given literal node by only concerning
  /// the list of given edges.
  /// @param lit The literal node.
  /// @param subgraph_edges The edges to "filter" by.
  /// @return The list of nodes adjacent to the literal node (incident to an
  /// edge passed as parameter).
  std::vector<feature_id>
  get_neighbors(feature_id lit,
                const std::vector<feature_pair> &subgraph_edges) const {
    std::vector<feature_id> neighbors;
    for (const auto &[p, q] : subgraph_edges) {
      if (!has_edge(p, q))
        continue;

      if (p == lit) {
        neighbors.push_back(q);
      } else if (q == lit) {
        neighbors.push_back(p);
      }
    }
    return neighbors;
  }

  /// @brief Finds all non-neighbors of the given literal node by only
  /// concerning non-edges
  /// @param lit The literal node.
  /// @param subgraph_edges The edges to "filter" by.
  /// @return The list of nodes adjacent to the literal node (incident to an
  /// edge passed as parameter).
  std::vector<feature_id> get_non_neighbors(feature_id lit) const {
    std::vector<feature_id> neighbors;
    for (feature_id i = -(feature_id)this->num_vars;
         i <= (feature_id)this->num_vars; i++) {
      if (i == lit || i == 0)
        continue;

      if (!has_edge(i, lit)) {
        neighbors.push_back(i);
      }
    }
    return neighbors;
  }

  /// @brief Builds a vector with all unique edges of the graph that pass the
  /// predicate. This should be much more efficient than calling get_all_edges.
  /// @return The vector containing all edges passing the predicate.
  std::vector<feature_pair>
  get_edges(const std::function<bool(const feature_pair &)> &predicate) const {
    std::vector<feature_pair> edges;

    for (feature_id i = -this->num_vars; i <= (feature_id)this->num_vars; i++) {
      for (feature_id j = i + 1; j <= (feature_id)this->num_vars; j++) {
        if (i != 0 && j != 0) {
          if (has_edge(i, j) && predicate({i, j})) {
            edges.push_back({i, j});
          }
        }
      }
    }

    return edges;
  }

  /// @brief Builds a vector with all unique edges of the graph.
  /// @return The vector containing all edges.
  std::vector<feature_pair> get_all_edges() const {
    std::vector<feature_pair> edges;

    for (feature_id i = -this->num_vars; i <= (feature_id)this->num_vars; i++) {
      for (feature_id j = i + 1; j <= (feature_id)this->num_vars; j++) {
        if (i != 0 && j != 0) {
          if (has_edge(i, j)) {
            edges.push_back({i, j});
          }
        }
      }
    }

    return edges;
  }

  /// @brief Constructs the transaction graph for a given instance by building
  /// the complement graph using the instance's known conflicts.
  /// @param instance The instance.
  /// @return the transaction graph of the instance.
  static TransactionGraph from_instance(const Instance &instance) {
    return TransactionGraph::from_conflicts(instance.n_concrete,
                                            instance.conflicts);
  }

  /// @brief Constructs the transaction graph by building
  /// the complement graph using an instance's known conflict edges.
  /// @param n_concrete The number of concrete features in the instance.
  /// @param conflicts The vector of conflicting feature pairs.
  /// @return The transaction graph (complement of the conflict graph)
  static TransactionGraph
  from_conflicts(const size_t n_concrete,
                 const std::vector<feature_pair> &conflicts) {
    TransactionGraph graph(n_concrete);
    for (const auto &conflict : conflicts) {
      graph.add_edge(conflict.first, conflict.second);
    }
    graph.complement();
    return graph;
  }

  /// @brief Finds and returns all unique nodes contained in the list of edges.
  /// @param edges The list of edges.
  /// @return A vector of nodes.
  std::vector<feature_id>
  unique_nodes_from_edgelist(const std::vector<feature_pair> &edges) const {
    std::unordered_set<feature_id> nodes;
    for (const auto &[p, q] : edges) {
      nodes.emplace(p);
      nodes.emplace(q);
    }
    return std::vector<feature_id>(nodes.begin(), nodes.end());
  }

  /// @brief Checks if the given two edges can be in a valid CDS. In other
  /// words, checks if the given edges do not appear in a clique of the graph.
  /// @param e1 The first edge.
  /// @param e2 The first edge.
  /// @return True, if the edges are clique disjoint. False, if not.
  bool are_edges_clique_disjoint(const feature_pair &e1,
                                 const feature_pair &e2) const {
    const auto &[u, v] = e1;
    const auto &[p, q] = e2;

    return (u != p && v != p && u != q && v != q &&
            !(has_edge(u, p) && has_edge(u, q) && has_edge(v, p) &&
              has_edge(v, q))) ||
           (u == p && v != q && !has_edge(v, q)) ||
           (u == q && v != p && !has_edge(v, p)) ||
           (v == p && u != q && !has_edge(u, q)) ||
           (v == q && u != p && !has_edge(u, p));
  }

  /// @brief Checks if every two edges in the vector can be in a valid CDS. In
  /// other words, checks if no two edges of the given edges appear in a clique
  /// of the graph.
  /// @param edges The vector of edges to test against.
  /// @return False, if any two edges of the vector are in a clique. True, if
  /// all edges are disjoint.
  bool are_edges_clique_disjoint(const std::vector<feature_pair> &edges) const {
    for (size_t i = 0; i < edges.size(); i++) {
      for (size_t j = i + 1; j < edges.size(); j++) {
        if (!are_edges_clique_disjoint(edges[i], edges[j])) {
          return false;
        }
      }
    }

    return true;
  }

  /// @brief A greedy method for finding large cliques in the complement of the
  /// graph (important for cds heuristic algo) This method finds multiple,
  /// disjoint cliques, which number can be specified via the parameters. The
  /// cliques are returned sorted by size, descending.
  /// @return A list of cliques in the complement graph.
  std::vector<std::vector<feature_id>>
  complement_clique_heuristic(size_t num_cliques = 5) const {
    // list of all nodes in vector
    std::vector<feature_id> vertices;
    for (feature_id i = 1; i <= (feature_id)num_vars; i++) {
      vertices.push_back(-i);
      vertices.push_back(i);
    }

    std::random_device rd;
    std::mt19937 random_generator(rd());

    // sort ascending by number of neighbors, so that first element has highest
    // amount of non-neighbors
    std::shuffle(vertices.begin(), vertices.end(), random_generator);
    std::stable_sort(vertices.begin(), vertices.end(),
                     [&](const feature_id &v, const feature_id &u) {
                       return count_neighbors(v) < count_neighbors(u);
                     });

    std::vector<std::vector<feature_id>> cliques(num_cliques);

    for (const auto &v : vertices) {
      for (auto &clique : cliques) {
        bool all_non_neighbors =
            std::all_of(clique.cbegin(), clique.cend(),
                        [&](const feature_id &u) { return !has_edge(u, v); });
        if (clique.empty() || all_non_neighbors) {
          clique.push_back(v);
          break;
        }
      }
    }

    // sort cliques so that biggest clique is at front
    std::sort(cliques.begin(), cliques.end(),
              [&](const std::vector<feature_id> &c1,
                  const std::vector<feature_id> &c2) {
                return c1.size() > c2.size();
              });
    /**
    std::cout << "CLIQUE: Found cliques of sizes: ";
    for (const auto &clique : cliques) {
      std::cout << clique.size() << " ";
    }
    std::cout << std::endl;
    */
    return cliques;
  }

private:
  /// @brief Calculates the encoded index of the literal.
  /// @param lit The literal. Negated literals are the variable (>=1) multiplied
  /// with -1.
  /// @return The theoretical row/column index of that literal in a square
  /// matrix.
  inline size_t lit_to_index(feature_id lit) const {
    assert(lit != 0);

    bool is_pos = lit > 0;
    return (size_t)(lit + this->num_vars - is_pos);
  }

  const size_t num_vars;
  const size_t num_nodes;
  const size_t num_cells; // the number of "cells" in the matrix (also maximum
                          // number of edges in the graph)
  size_t num_edges = 0;
  TriangularMatrix adjacency_matrix;
};
} // namespace samplns

#endif
