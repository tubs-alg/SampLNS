# = Experiment Configuration File =
# Centralizing all properties and paths within this configuration file simplifies management.
# By decoupling these elements from the code, adjustments can be made effortlessly.
# Consequently, replicating and customizing this experiment becomes a seamless process.

INSTANCE_ARCHIVE = "../benchmark_models.zip"
BASELINE_ARCHIVES = [
    "./EXTERNAL_INPUT/baseline.zip",
]
YASA_15MIN_DATA = "../06_yasa_15min/simplified_data.json.xz"