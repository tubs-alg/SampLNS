import os.path
from zipfile import ZipFile

import pandas as pd
from samplns.instances import parse_source


def get_instance(instance_name, archive_path):
    """
    Simple helper to parse instance
    """
    with ZipFile(archive_path) as archive:
        with archive.open(os.path.join(instance_name, "model.xml")) as f:
            return parse_source(f, instance_name)


def parse_solution_overview(path, subpath=None):
    """
    ['ModelID', 'AlgorithmID', 'SystemIteration', 'AlgorithmIteration',
       'InTime', 'Success', 'Time', 'SampleSize', 'Instance', '#Variables',
       '#Clauses', 'Algorithm', 'Settings', 'Path']
    """
    if subpath is None:
        with ZipFile(path) as archive:
            ext = "data/data.csv"
            data_folders = {
                f.filename[: -len(ext)]
                for f in archive.filelist
                if f.filename.endswith(ext)
            }
            print("Found the data folders:", data_folders)
        return pd.concat(
            (parse_solution_overview(path, df) for df in data_folders),
            ignore_index=True,
        )
    if subpath and not subpath.endswith("/"):
        subpath += "/"
    with ZipFile(path) as archive:
        with archive.open(f"{subpath if subpath else ''}data/data.csv") as f:
            data = pd.read_csv(f, sep=";")
        with archive.open(f"{subpath if subpath else ''}data/models.csv") as f:
            models = pd.read_csv(f, sep=";")
            models.rename(columns={"Name": "Instance"}, inplace=True)
        with archive.open(f"{subpath if subpath else ''}data/algorithms.csv") as f:
            algorithms = pd.read_csv(f, sep=";")
            algorithms.rename(columns={"Name": "Algorithm"}, inplace=True)
        t = data.merge(models, right_on="ModelID", left_on="ModelID")
        t = t.merge(algorithms, on="AlgorithmID")

        def f(row):
            return (
                f"{subpath}{row['ModelID']}_{row['SystemIteration']}_{row['AlgorithmID']}_{row['AlgorithmIteration']}_sample.csv"
                if row["SampleSize"] > 0
                else None
            )

        t["Path"] = t.apply(f, axis=1)
        return t


def parse_sample(archive_path, sample_path):
    with ZipFile(archive_path) as archive, archive.open(sample_path) as f:
        t = pd.read_csv(f, sep=";", index_col="Configuration")
        samples = []

        def f(row):
            samples.append({k: v == "+" for k, v in row.items()})

        t.apply(f, axis=1)
        return samples


def get_results(input_sample_archive, result_folder, max_vars=1500):
    # Loading the data of the experiment.
    from aemeasure import read_as_pandas_table

    # Merge the new data with the data of the initial samples
    data = read_as_pandas_table(result_folder)
    data_initial = parse_solution_overview(input_sample_archive)
    data = data.merge(data_initial, left_on="initial_sample_path", right_on="Path")

    # add a good name for 00_baseline algorithms including the settings
    def baseline_alg_name(row):
        settings = row["Settings"]
        if "_m" in settings:
            m = settings.split("_m")[-1].split("_")[0]
            return f"{row['Algorithm']}(m={m})"
        return row["Algorithm"]

    data["baseline_alg"] = data.apply(baseline_alg_name, axis=1)
    n = len(data)
    data = data[data["#Variables"] <= max_vars].copy()
    print(f"Removed {n-len(data)} results because of size constraint.")
    return data
