# = Experiment Configuration File =
# Centralizing all properties and paths within this configuration file simplifies management.
# By decoupling these elements from the code, adjustments can be made effortlessly.
# Consequently, replicating and customizing this experiment becomes a seamless process.

ITERATIONS = 10000
ITERATION_TIME_LIMIT = 60.0
CDS_ITERATION_TIME_LIMIT = 60.0
TIME_LIMIT = 15 * 60

BASE = "baseline"
RESULT_FOLDER = f"DATA/samplns_results/{BASE}_{TIME_LIMIT}"
INPUT_SAMPLE_ARCHIVE = f"../00_baseline/EXTERNAL_INPUT/{BASE}.zip"
INSTANCE_ARCHIVE = "../benchmark_models.zip"

EXTERNAL_BOUNDS = [
    #  "../02_60min_samplns_2023-08-19/out/06_best_bounds.csv",
    #  "../03_60min_samplns_long_iterations_2023-08-19/out/06_best_bounds.csv",
    "../01_samplns_2023-08-19/OUTPUT/06_best_bounds.csv",
    "../04_super_long_samplns/OUTPUT/06_best_bounds.csv",
]
EXTENDED_BASELINE_DATA = "../00_baseline/OUTPUT/01_simple_baseline_data.json.zip"
BASELINE_SELECTIONS = [
    {"Algorithm": "FIDE-YASA", "Settings": "t2_m1_null"},
    {"Algorithm": "FIDE-YASA", "Settings": "t2_m10_null"},
    {"Algorithm": "Incling", "Settings": "t2"},
    {"Algorithm": "FIDE-ICPL", "Settings": "t2"},
]


PREPROCESSED_RESULTS = "./OUTPUT/04_preprocessed_data.json.zip"

# Plots
PLOT_WIDTH = 6.0
PLOT_INITIAL_SAMPLE_COMPARISON = "./OUTPUT/05_initial_sample_comparison.pdf"
PLOT_INITIAL_SAMPLE_COMPARISON_BOXPLOT = (
    "./OUTPUT/05_initial_sample_comparison_boxplot.pdf"
)
