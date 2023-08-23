# All general properties and dependencies of this experiment and evaluation should be defined here.

ITERATIONS = 10000
ITERATION_TIME_LIMIT = 60.0
TIME_LIMIT = 900

BASE = "900_seconds_5_it"
RESULT_FOLDER = f"01_results/{BASE}_{TIME_LIMIT}"
INPUT_SAMPLE_ARCHIVE = f"../00_baseline/EXTERNAL_INPUT/{BASE}.zip"
INSTANCE_ARCHIVE = "./EXTERNAL_INPUT/extended_benchmark_instances.zip"
EXTENDED_BASELINE_DATA = "../00_baseline/OUTPUT/01_simple_baseline_data.json.zip"
EXTERNAL_BOUNDS = [
    "../02_60min_samplns_2023-08-19/out/06_best_bounds.csv",
    "../03_60min_samplns_long_iterations_2023-08-19/out/06_best_bounds.csv",
]
