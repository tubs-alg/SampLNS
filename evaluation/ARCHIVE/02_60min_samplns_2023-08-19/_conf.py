# = Experiment Configuration File =
# Centralizing all properties and paths within this configuration file simplifies management.
# By decoupling these elements from the code, adjustments can be made effortlessly.
# Consequently, replicating and customizing this experiment becomes a seamless process.

ITERATIONS = 10000
ITERATION_TIME_LIMIT = 60.0
TIME_LIMIT = 60 * 60

BASE = "900_seconds_5_it"
RESULT_FOLDER = f"DATA/01_results/{BASE}_{TIME_LIMIT}"
INPUT_SAMPLE_ARCHIVE = f"../00_baseline/EXTERNAL_INPUT/{BASE}.zip"
INSTANCE_ARCHIVE = "../benchmark_models.zip"

EXTENDED_BASELINE_DATA = "../00_baseline/OUTPUT/01_simple_baseline_data.json.zip"
EXTERNAL_BOUNDS = [
    "../02_60min_samplns_2023-08-19/out/06_best_bounds.csv",
    "../03_60min_samplns_long_iterations_2023-08-19/out/06_best_bounds.csv",
]
