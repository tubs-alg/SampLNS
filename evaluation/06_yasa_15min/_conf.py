# = Experiment Configuration File =
# Centralizing all properties and paths within this configuration file simplifies management.
# By decoupling these elements from the code, adjustments can be made effortlessly.
# Consequently, replicating and customizing this experiment becomes a seamless process.

RESULT_FOLDER = "./results"
INSTANCE_ARCHIVE = "../benchmark_models.zip"
BASELINE_ARCHIVES = [
    "../00_baseline/EXTERNAL_INPUT/baseline.zip",
    "../00_baseline/EXTERNAL_INPUT/900_seconds_5_it.zip",
]
SIMPLIFIED_DATA = "./simplified_data.json.xz"