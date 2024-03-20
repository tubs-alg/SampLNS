import pandas as pd

from pathlib import Path
from zipfile import ZipFile
import subprocess
import tomllib

with (Path(__file__).parent / ".." / "config.toml").open("rb") as f:
    config = tomllib.load(f)
    config_exp = config[Path(__file__).parent.name]
INSTANCES = config["benchmark"]["instance_names"]

from pathlib import Path


def parse_sample_file(f):
    t = pd.read_csv(f, sep=";", index_col="Configuration")
    samples = []

    def f(row):
        samples.append({k: v == "+" for k, v in row.items()})

    t.apply(f, axis=1)
    return samples


if __name__ == "__main__":
    data = {
        "instance": [],
        "sample_size": [],
        "path": [],
        "sample": [],
    }

    for solution_path in Path(config_exp["result_folder"]).rglob("*.csv"):
        instance_name = solution_path.parts[-2]
        sample_idx = int(solution_path.name.split("_")[1].split(".")[0])
        with open(solution_path) as f:
            sample = parse_sample_file(f)
        print(f"{instance_name} {sample_idx} {len(sample)}")
        data["instance"].append(instance_name)
        data["sample_size"].append(len(sample))
        data["sample"].append(sample)
        data["path"].append(str(solution_path.absolute()))
    Path(config_exp["result_table"]).parent.mkdir(exist_ok=True, parents=True)
    df = pd.DataFrame(data)
    df.drop(columns=["sample"]).to_json(config_exp["result_table"])
    df.to_json(config_exp["sample_table"])
