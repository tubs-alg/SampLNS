# All general properties and dependencies of this experiment and evaluation should be defined here.

ITERATIONS = 10000
ITERATION_TIME_LIMIT = 60.0
TIME_LIMIT = 900

BASE = "900_seconds_5_it"
RESULT_FOLDER = f"01_results/{BASE}_{TIME_LIMIT}"
INPUT_SAMPLE_ARCHIVE = f"../01_ICSE_2024_0/00_baseline/{BASE}.zip"
INSTANCE_ARCHIVE = "../../benchmark_models.zip"
EXTENDED_BASELINE_DATA = "../05_baseline/03_simple_baseline_data.json.zip"
EXTERNAL_BOUNDS = ["../07_long_optimization/out/06_best_bounds.csv", "../08_longer_iterations/out/06_best_bounds.csv"]