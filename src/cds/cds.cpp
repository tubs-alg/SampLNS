#include "cds/cds.hpp"
#include "cds/cds_heuristic.hpp"
#include "cds/cds_operations.hpp"
#include <iostream>
#include <stdexcept>

using samplns::json;

std::vector<Edge>
CDSSolverInterface::optimize(std::vector<Edge> initial_solution,
                             unsigned int max_iterations, double time_limit,
                             bool verbose) {
  
  if (this->graph->count_edges() == 0) {
    // WARNING: Transaction Graph is empty
    return std::vector<Edge>();
  }
  
  ensure_threadsafety_mtx.lock();

  if (!initial_solution.empty()) {
    try {
      cds_check_solution(*graph, initial_solution);
    } catch (const std::runtime_error &e) {
      throw std::runtime_error("The initial solution is invalid: " +
                               std::string(e.what()));
    }
  }

  // find initial solution if none provided
  if (solver.get_best_solution().size() == 0 && initial_solution.size() == 0) {
    if (use_heur && subgraph.empty()) {
      std::cout << "No initial solution. Searching for one using MIS..."
                << std::endl;
      CDSNodeHeuristic heur(*graph, initial_solution);
      heur.optimize(3, 10.0, false); // search for some iterations
      initial_solution = heur.get_best_solution();
    } else {
      std::cout << "No initial solution. Fixing one single edge..."
                << std::endl;
      for (feature_id i = 1; i < (feature_id)graph->count_nodes() / 2; i++) {
        auto nbs = graph->get_neighbors(i);
        std::shuffle(nbs.begin(), nbs.end(), rng());
        if (nbs.size() > 0) {
          feature_id j = nbs[0];
          if (i > j) {
            std::swap(i, j);
          }
          initial_solution.push_back({i, j});
          break;
        }
      }
    }
  }

  if (!initial_solution.empty() &&
      initial_solution.size() > solver.get_best_solution().size()) {
    // std::cout << "Using initial solution of size " << initial_solution.size()
    //           << "." << std::endl;
  }

  // Force ordering of vertices in edges
  for (auto &[p, q] : initial_solution) {
    if (p > q) {
      std::swap(p, q);
    }
  }

  // update solution, optimize
  solver.add_solution(initial_solution);
  solver.optimize(max_iterations, time_limit, verbose);
  this->is_optimal = solver.is_optimal_solution(solver.get_best_solution());

  const auto &solution = solver.get_best_solution();

  // check solution
  cds_check_solution(*graph, solution);

  ensure_threadsafety_mtx.unlock();

  return solution;
}

bool AsyncCDSSolverInterface::start(std::vector<Edge> initial_solution,
                                    double iteration_timelimit) {
  // try to lock the semaphore
  bool can_spawn = spawn_thread_guard.try_wait();
  if (!can_spawn) {
    std::cerr << "WARNING: Can not start async CDS solver as the worker is "
                 "already (or still) running!"
              << std::endl;
    return false;
  }

  // semaphore was locked successfully

  this->do_stop.store(false);
  this->time_limit.store(iteration_timelimit);

  std::function<void(std::vector<Edge>)> task = std::bind(
      &AsyncCDSSolverInterface::worker_optimize, this, std::placeholders::_1);
  std::thread worker(task, initial_solution);
  worker.detach();

  return true;
}
