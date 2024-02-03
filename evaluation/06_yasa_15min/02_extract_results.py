import pandas as pd
from _conf import SIMPLIFIED_DATA, RESULT_FOLDER
from _utils import parse_sample_file

from pathlib import Path

if __name__ == "__main__":
    data = {
        "instance": [],
        "sample_size": [],
        "path": [],
    }

    for solution_path in Path(RESULT_FOLDER).rglob("*.csv"):
        instance_name = solution_path.parts[1]
        sample_idx = int(solution_path.name.split("_")[1].split(".")[0])
        with open(solution_path) as f:
            sample = parse_sample_file(f)
        print(f"{instance_name} {sample_idx} {len(sample)}")
        data["instance"].append(instance_name)
        data["sample_size"].append(len(sample))
        data["path"].append(str(solution_path.absolute()))

    df = pd.DataFrame(data)
    print(df)
    print("Writing to", SIMPLIFIED_DATA)
    df.to_json(Path(SIMPLIFIED_DATA))
    