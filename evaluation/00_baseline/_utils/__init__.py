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
        t["ArchivePath"] = path
        return t


def parse_sample(archive_path, sample_path):
    with ZipFile(archive_path) as archive, archive.open(sample_path) as f:
        t = pd.read_csv(f, sep=";", index_col="Configuration")
        samples = []

        def f(row):
            samples.append({k: v == "+" for k, v in row.items()})

        t.apply(f, axis=1)
        return samples
