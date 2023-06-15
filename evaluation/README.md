# Evaluation

This folder contains the experiments and evaluations of the algorithm.

## Structure

Evaluations should follow the following structure that enables a proper
documentation and reproducibility.

- Have everything numbered in the way things were created/run.
- Make output files in a way that you can easily find their origin. Often you
  have to copy some results and then a year later you want to know where you got
  it from.
- Add as many README.md as possible, even if they just say who and when did
  this. Better also write in a sentence the initial motivation. This is very
  quickly done and can help tremendously a year later when you have to look into
  the results again for some reason.

This structure is just an example and does not match the actual experiments.

- `README.md` This file. Give an overview of the experiments and the structure.
- `00_experiment_a/` A first experiment.
  - `00_input_data/`
  - `01_prepare_input.py`
  - `02_run_experiment.py`
  - `03_process_results.py`
  - `03_processed_results/`
  - `04_analyze_something.ipynb`
- `01_experiment_b/`
  - `README.md` Describe the experiment.
  - `00_benchmark_instances/`
    - `README.md` Describe the format of the benchmark instances.
  - `01_run_old_algorithms/`
    - `00_prepare_instances.py`
    - `01_run_old_algorithms.py`
    - `02_process_results.py`
    - `02_results/`
    - `03_first_look.ipynb` Quick look into the results to make sure they look
      as expected.
  - `02_run_new_algorithm/`
    - `00_prepare_instances.py`
    - `01_run_new_algorithm.py`
    - `02_process_results.py`
    - `02_results/`
    - `03_first_look.ipynb` Quick look into the results to make sure they look
      as expected.
  - `03_compare_algorithms.ipynb` Compare the performance of algorithms in some
    plots.
