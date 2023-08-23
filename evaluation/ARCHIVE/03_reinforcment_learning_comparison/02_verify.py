from _utils import *
from samplns.verify import have_equal_coverage


def parse_ril_solutions(instance, path):
    with open(path) as f:
        lines = f.readlines()
        sample = [{} for _ in lines[0].split(",")]
        for f, line in enumerate(lines[1:]):
            for i, value in enumerate(line.split(",")):
                sample[i][instance.features[f]] = bool(int(value))
    return sample


if __name__ == "__main__":
    instance_name = "BerkeleyDBC"
    instance = get_instance(instance_name)
    ril_sample = parse_ril_solutions(
        instance,
        "00_data/Results_RLSampler/BerkeleyDBC/t_2/BerkeleyDBC_t_2_sample_RL.csv",
    )
    yasa_sample = parse_sample(instance, instance_name, "YASA_2")
    for conf in ril_sample:
        print(conf)
        assert instance.is_feasible(conf)
    for conf in yasa_sample:
        print(conf)
        assert instance.is_feasible(conf)
    assert have_equal_coverage(instance, ril_sample, yasa_sample)
