ITERATIONS = 10000
ITERATION_TIME_LIMIT = 60.0
CDS_ITERATION_TIME_LIMIT = 60.0
TIME_LIMIT = 15 * 60

BASE = "900_seconds_5_it"
RESULT_FOLDER = f"DATA/samplns_results/{BASE}_{TIME_LIMIT}"
INPUT_SAMPLE_ARCHIVE = f"../00_baseline/EXTERNAL_INPUT/{BASE}.zip"
INSTANCE_ARCHIVE = "../benchmark_models.zip"

EXTERNAL_BOUNDS = [
    "../02_60min_samplns_2023-08-19/out/06_best_bounds.csv",
    "../03_60min_samplns_long_iterations_2023-08-19/out/06_best_bounds.csv",
]
EXTENDED_BASELINE_DATA = "../00_baseline/OUTPUT/01_simple_baseline_data.json.zip"
BASELINE_SELECTIONS = [
    {"Algorithm": "FIDE-YASA", "Settings": "t2_m1_null"},
    {"Algorithm": "FIDE-YASA", "Settings": "t2_m10_null"},
    {"Algorithm": "Incling", "Settings": "t2"},
]

# DATA

PREPROCESSED_RESULTS = "./OUTPUT/04_clean_data.json.zip"