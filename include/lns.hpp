#ifndef ALG_SCP_LNS_HPP
#define ALG_SCP_LNS_HPP

#include <atomic>
#include <chrono>
#include <functional>
#include <iostream>
#include <memory>
#include <vector>

#include "timer.hpp"

namespace samplns {

inline std::mt19937_64 &rng() noexcept {
  static std::atomic<std::int32_t> counter(0);
  thread_local std::mt19937_64 res(1337 + counter++);
  return res;
}

template <typename solution_type> struct Neighborhood {
  solution_type fixed_solution;
  solution_type free_solution;

  Neighborhood() {}

  Neighborhood(solution_type fixed_solution, solution_type free_solution) {
    this->fixed_solution = fixed_solution;
    this->free_solution = free_solution;
  }
};

template <typename instance_type, typename solution_type>
class NeighborhoodSelector {
public:
  const instance_type &instance;

  explicit NeighborhoodSelector(const instance_type &instance)
      : instance(instance) {}

  /// @brief Allows the solver to give feedback on the neighborhood.
  /// @param neighborhood should be the previous neighborhood.
  /// @param solution the solution for that neighborhood found by the LNS.
  /// @param time_utilization >=0.99 slow. ~0 very fast.
  /// @param nb_utilization >=0.99 most of the time is spent calculating the
  /// nbhd, ~0 almost all time is used on solving nbhd to optimality (which is
  /// desirable)
  virtual void feedback(Neighborhood<solution_type> &neighborhood,
                        const solution_type &solution, double time_utilization,
                        double nb_utilization) {
    // default: feedback ignored
  }

  /// @brief Lets the neighborhood selector know about a new, better solution.
  /// @param solution The better solution.
  virtual void better_solution_callback(const solution_type &solution) {}

  /// @brief Calculates and returns the next neighborhood.
  /// @return The next neighborhood.
  virtual Neighborhood<solution_type> next() = 0;

  virtual ~NeighborhoodSelector() = default;
};

template <typename instance_type, typename solution_type> class ModularLNS {
public:
  ModularLNS(NeighborhoodSelector<instance_type, solution_type> *nb_selector,
             const solution_type &initial_solution)
      : nb_selector(nb_selector), best_solution(initial_solution) {}

  /// @brief Used by the solver to notify you about new solutions. Does not have
  /// to be better solution!
  /// @param solution The new solution produced by the LNS.
  virtual void new_solution_callback(const solution_type &solution) = 0;

  /// @brief Used as a check for the generic LNS algorithm if a found solution
  /// is better than the current best. Must be implemented by a subclass.
  /// @param solution The found solution.
  /// @return True if the new solution is better, false if not.
  virtual bool is_better_solution(const solution_type &solution) const = 0;

  /// @brief Used to implement a feedback for the solver to know wether a found
  /// solution is optimal. For most LNS approaches, it is impossible to know if
  /// a solution is optimal. Default implementation just returns false, but can
  /// be overriden.
  /// @param solution The solution to check.
  /// @return True if optimal, false if not.
  virtual bool is_optimal_solution(const solution_type &solution) const {
    return false;
  }

  const solution_type &get_best_solution() const { return best_solution; }

  /// @brief Performs a LNS optimization on the given neighborhood.
  /// @param neighborhood The neighborhood to optimize on.
  /// @param timelimit The time limit per iteration in seconds.
  virtual solution_type
  optimize_neighborhood(Neighborhood<solution_type> &neighborhood,
                        double timelimit) = 0;

  /// @brief Interface for letting the framework know about a solution acquired
  /// by any means. This will automatically update the best solution (if better
  /// than best known) and call all related callbacks.
  /// @param solution The solution to be added.
  /// @return True, if the solution was better than any known solution. False,
  /// otherwise.
  bool add_solution(const solution_type &solution) {
    bool improvement = is_better_solution(solution);
    if (improvement) {
      this->best_solution = solution;
      nb_selector->better_solution_callback(solution);
      for (const auto &func : better_solution_callbacks) {
        func(solution);
      }
    }
    new_solution_callback(solution);
    return improvement;
  }

  void add_better_solution_callback(
      std::function<void(const solution_type &)> callback) {
    this->better_solution_callbacks.push_back(callback);
  }

  bool optimize(int iterations = 15, double iteration_timelimit = 60.0f,
                bool verbose = false) {

    this->verbose = verbose;

    if (this->optimal_) {
      if (verbose) {
        std::cout << "Skipping optimization because of optimality!"
                  << std::endl;
      }
      return true;
    }

    if (verbose) {
      std::cout << "Optimization started. #iterations: " << iterations
                << ", #secpit: " << iteration_timelimit << "." << std::endl;
    }

    for (int i = 1; i <= iterations && !optimal_; i++) {

      new_iteration(i);
      set_iteration_statistic("iter_start", timestamp());

      // measure time for neighborhood heuristic
      timer.start();
      set_iteration_statistic("nbhd_start", timestamp());
      Neighborhood<solution_type> nbhd = nb_selector->next();
      set_iteration_statistic("nbhd_stop", timestamp());
      double nbhd_time = timer.elapsed();

      // measure time for optimization subroutine
      set_iteration_statistic("optimize_start", timestamp());
      solution_type solution =
          this->optimize_neighborhood(nbhd, iteration_timelimit);
      set_iteration_statistic("optimize_stop", timestamp());

      timer.stop();
      double totdiff = timer.elapsed();

      double tutil = totdiff / iteration_timelimit;

      if (verbose) {
        std::cout << "Iteration took " << totdiff << " seconds. (" << nbhd_time
                  << " for nbhd construction)" << std::endl;
      }

      if (add_solution(solution)) {
        if (verbose) {
          std::cout << "Better solution found!" << std::endl;
        }
      }

      if (is_optimal_solution(solution)) {
        this->optimal_ = true;
        if (verbose) {
          std::cout << "The found solution was optimal!" << std::endl;
        }
        break;
      }

      nb_selector->feedback(nbhd, solution, tutil, nbhd_time / totdiff);

      set_iteration_statistic("iter_stop", timestamp());
      end_iteration();
    }

    return this->optimal_;
  }

  const auto &get_iteration_statistics() const { return iteration_statistics; }

protected:
  void set_iteration_statistic(std::string key, int64_t value) {
    this->iteration_statistics.back().insert_or_assign(key, value);
  }
  int64_t timestamp() { return timer.timestamp(); }
  bool verbose = false;

private:
  bool optimal_ = false;
  std::vector<std::unordered_map<std::string, int64_t>> iteration_statistics;
  std::unique_ptr<NeighborhoodSelector<instance_type, solution_type>>
      nb_selector;
  std::vector<std::function<void(const solution_type &)>>
      better_solution_callbacks;
  solution_type best_solution;
  Timer timer;

  void new_iteration(int i) {
    if (verbose) {
      std::cout << "Started iteration " << i << "." << std::endl;
    }
    iteration_statistics.push_back(std::unordered_map<std::string, int64_t>());
  }

  void end_iteration() {
    if (this->optimal_) {
      if (verbose) {
        std::cout << "LNS found optimal solution!" << std::endl;
      }
    }
    if (verbose) {
      std::cout << "Done." << std::endl;
      std::cout << "Iteration statistics: "
                << ((json)iteration_statistics.back()).dump() << std::endl;
    }
  }
};

template <typename instance_type, typename solution_type>
class LowerBoundLNS : public ModularLNS<instance_type, solution_type> {
public:
  LowerBoundLNS(NeighborhoodSelector<instance_type, solution_type> *nb_selector,
                const solution_type &initial_solution)
      : ModularLNS<instance_type, solution_type>(nb_selector,
                                                 initial_solution) {}

  int64_t get_lb() const { return this->lb; }

  virtual int64_t get_solution_score(const solution_type &solution) const = 0;

  void new_solution_callback(const solution_type &solution) override {
    this->update_lb(this->get_solution_score(solution));
  }

  bool is_better_solution(const solution_type &solution) const override {
    return get_solution_score(solution) > lb;
  }

private:
  void update_lb(int64_t value) {
    if (value > this->lb && this->verbose) {
      std::cout << "--- " << value << " ---" << std::endl;
    }
    this->lb = std::max(this->lb, value);
  }

  int64_t lb = INT64_MIN;
};

} // namespace samplns

#endif
