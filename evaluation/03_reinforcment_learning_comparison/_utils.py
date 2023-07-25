from samplns.instances import Instance, parse_dimacs

def parse_sample(instance: Instance, instance_name: str, method: str):
    with open(f"00_data/feature_models/{instance_name}/{instance_name}_sample_{method}.csv") as f:
        lines = f.readlines()
        sample = [dict() for _ in lines[0].split(",")[1:]]
        for f, line in enumerate(lines[1:]):
            if not line:
                continue  # empty line
            for i, value in enumerate(line.split(",")[1:]):
                sample[i][instance.features[f]] = bool(int(value))
        print(sample)
        for conf in sample:
            #conf["__Root__"] = True
            assert instance.is_feasible(conf, verbose=True)
        return sample

def get_instance(instance_name: str):
    return parse_dimacs(f"00_data/feature_models/{instance_name}/{instance_name}.dimacs")