ITERATIONS = 10000
ITERATION_TIME_LIMIT = 180.0
CDS_ITERATION_TIME_LIMIT = 180.0
TIME_LIMIT = 3 * 60 * 60

BASE = "900_seconds_5_it"
RESULT_FOLDER = f"DATA/01_results/{BASE}_{TIME_LIMIT}"
INPUT_SAMPLE_ARCHIVE = f"../00_baseline/EXTERNAL_INPUT/{BASE}.zip"
INSTANCE_ARCHIVE = "../benchmark_models.zip"

EXTENDED_BASELINE_DATA = "../00_baseline/OUTPUT/01_simple_baseline_data.json.zip"
EXTERNAL_BOUNDS = [
    "../01_samplns_2023-08-19/OUTPUT/06_best_bounds.csv",
]

PREPROCESSDED_RESULTS = "./OUTPUT/04_preprocessed_data.json.zip"
EXPORT_BEST_BOUNDS = "./OUTPUT/06_best_bounds.csv"
EXPORT_AVG_FINAL_TIME = "./OUTPUT/07_avg_final_time.csv"