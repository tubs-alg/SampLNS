#ifndef ALG_SCP_CDS_HPP
#define ALG_SCP_CDS_HPP

#include "cds/cds_lns.hpp"
#include "graph.hpp"
#include "instance.hpp"
#include "parser.hpp"
#include <atomic>
#include <condition_variable>
#include <mutex>
#include <thread>

using namespace samplns;
using Edge = samplns::feature_pair;

/// @brief A simple semaphore implementation for standards prior to C++ 20
/// Access to the counter variable is locked by a mutex and waiting/notifying
/// is handled using a std::condition_variable
class Semaphore {
public:
  Semaphore(int count = 0) : count_(count) {}

  void notify() {
    std::unique_lock<std::mutex> lock(mutex_);
    ++count_;
    cv_.notify_one();
  }

  void wait() {
    std::unique_lock<std::mutex> lock(mutex_);
    while (count_ <= 0) {
      cv_.wait(lock);
    }
    --count_;
  }

  bool try_wait() {
    std::unique_lock<std::mutex> lock(mutex_);
    if (count_ <= 0) {
      return false;
    }
    --count_;
    return true;
  }

private:
  std::mutex mutex_;
  std::condition_variable cv_;
  volatile int count_;
};

/// @brief This class is designed to be directly used through the python
/// interface
class CDSSolverInterface {
public:
  CDSSolverInterface(TransactionGraph *graph, std::vector<Edge> subgraph = {},
                     bool use_heur = false, bool be_smart = true)
      : graph(graph), subgraph(subgraph), use_heur(use_heur),
        solver(*graph, std::vector<Edge>(), subgraph, be_smart) {
    // seed the rng with system time
    const auto seed = std::time(0);
    std::srand(seed);

    // test the graph
    graph->test();
    std::cout << "The graph has " << graph->count_edges() << " edges and "
              << graph->count_nodes() << " nodes." << std::endl;

    std::cout << "The subgraph has " << subgraph.size() << " edges."
              << std::endl;
  }

  std::vector<Edge> optimize(std::vector<Edge> initial_solution,
                             unsigned int max_iterations, double time_limit,
                             bool verbose);

  const auto get_iteration_statistics() const {
    return solver.get_iteration_statistics();
  }

  CDSSolver &get_internal_solver() { return solver; }

  bool has_optimal_solution() const { return is_optimal; }

private:
  bool is_optimal = false;
  const TransactionGraph *graph;
  const std::vector<Edge> subgraph;
  const bool use_heur;
  CDSSolver solver; // solver based on LNS approach
  std::mutex ensure_threadsafety_mtx;
};

/// @brief This class is designed to be directly used through the python
/// interface, but all the computations to be executed in a seperate daemon
/// thread (in C++)
class AsyncCDSSolverInterface {
public:
  AsyncCDSSolverInterface(TransactionGraph *graph)
      : graph(graph), solver(graph) {
    std::function<void(const std::vector<Edge> &)> callback =
        std::bind(&AsyncCDSSolverInterface::update_best_solution, this,
                  std::placeholders::_1);
    solver.get_internal_solver().add_better_solution_callback(callback);
  }

  bool start(std::vector<Edge> initial_solution, double iteration_timelimit);

  void stop() {
    if (do_stop.load())
      return;

    // signal worker thread to stop
    do_stop.store(true);

    // wait for the worker thread to unlock the guard (by that signaling that it
    // terminated)
    spawn_thread_guard.wait();

    // unlock the guard again
    spawn_thread_guard.notify();
  }

  void update_best_solution(const std::vector<Edge> &solution) {
    std::unique_lock<std::mutex> lock(data_mtx);
    this->best_solution = solution;
  }

  void worker_optimize(std::vector<Edge> solution) {
    std::cout << "AsyncCDSLNS: Got initial solution of size " << solution.size()
              << "." << std::endl;
    while (!this->do_stop.load() && !this->solver.has_optimal_solution()) {
      this->solver.optimize(solution, 1, this->time_limit.load(), true);
    }
    this->spawn_thread_guard.notify();
    std::cout << "CDS LNS Worker thread stopped!" << std::endl;
  }

  std::vector<Edge> get_best_solution() {
    std::unique_lock<std::mutex> lock(data_mtx);
    auto sol = this->best_solution;
    if (!graph->are_edges_clique_disjoint(sol)) {
      throw std::runtime_error("The solution saved in the AsyncCDSSolver is "
                               "invalid! (Not disjoint)");
    }
    return sol;
  }

  const auto get_iteration_statistics() {
    std::unique_lock<std::mutex> lock(data_mtx);
    const auto stats = solver.get_iteration_statistics();
    return stats;
  }

private:
  const TransactionGraph *graph;
  CDSSolverInterface solver; // solver based on LNS approach
  std::vector<Edge> best_solution;

  // synchronization variables
  std::atomic<bool> do_stop{false};
  std::atomic<double> time_limit{60.0};
  std::mutex data_mtx;
  Semaphore spawn_thread_guard{
      1}; // assures that only one worker can exist at a time. Can't be
          // mutex as it is modified by multiple threads.
};

#endif
