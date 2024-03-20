"""
Extracting sharable pandas tables from the raw data.
"""

import tomllib
from pathlib import Path

if __name__ == "__main__":
    with Path("../config.toml").open("rb") as f:
        config = tomllib.load(f)

    EXPERIMENT = "samplns_15min"

    from algbench import describe, read_as_pandas

    describe(config[EXPERIMENT]["algbench_results"])

    t = read_as_pandas(
        config[EXPERIMENT]["algbench_results"],
        lambda data: {
            "instance_name": data["parameters"]["args"]["instance_name"],
            "lb": data["result"]["lower_bound"],
            "ub": data["result"]["upper_bound"],
            "iteration": data["parameters"]["args"]["rep"],
            "runtime": data["runtime"],
            "timestamp": data["timestamp"],
            "hostname": data["env"]["hostname"],
            "sample": data["result"]["solution"],
            "time_used_by_yasa": data["result"]["time_used_by_yasa"],
            "iteration_info": data["result"]["iteration_info"],
        },
    )
    Path(config[EXPERIMENT]["result_table"]).parent.mkdir(
        exist_ok=True, parents=True
    )
    t.drop(columns=["iteration_info", "sample"]).to_json(
        config[EXPERIMENT]["result_table"]
    )
    t.to_json(config[EXPERIMENT]["iteration_info"])
