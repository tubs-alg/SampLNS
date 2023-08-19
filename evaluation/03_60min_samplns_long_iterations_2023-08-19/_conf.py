ITERATIONS = 10000
ITERATION_TIME_LIMIT = 120.0
CDS_ITERATION_TIME_LIMIT = 120.0
TIME_LIMIT = 60*60

BASE = "900_seconds_5_it"
RESULT_FOLDER = f"01_results/{BASE}_{TIME_LIMIT}"
INPUT_SAMPLE_ARCHIVE = f"../01_samplns_2023-08-19/EXTERNAL_INPUT/{BASE}.zip"
INSTANCE_ARCHIVE = "../benchmark_models.zip"

EXTENDED_BASELINE_DATA = "../00_baseline/OUTPUT/01_simple_baseline_data.json.zip"
EXTERNAL_BOUNDS = ["../02_60min_samplns_2023-08-19/out/06_best_bounds.csv", "../03_60min_samplns_long_iterations_2023-08-19/out/06_best_bounds.csv"]