from _utils import get_instance, parse_sample
from algbench import Benchmark, describe
from samplns.verify import have_equal_coverage

TIME_LIMIT = 900
BASE = "900_seconds_5_it"
INPUT_SAMPLE_ARCHIVE = f"../01_ICSE_2024_0/00_baseline/{BASE}.zip"
INSTANCE_ARCHIVE = "../01_ICSE_2024_0/00_benchmark_instances.zip"
RESULT_FOLDER = f"01_results/{BASE}_{TIME_LIMIT}"

if __name__ == "__main__":
    data = Benchmark(RESULT_FOLDER)
    data_ = []
    describe(RESULT_FOLDER)
    for entry in data:
        if entry["result"] is None:
            continue  # empty entry, bad setup from me

        print("Check", entry["parameters"]["args"]["instance_name"])
        instance = get_instance(
            entry["parameters"]["args"]["instance_name"], INSTANCE_ARCHIVE
        )
        lns_sample = entry["result"]["solution"]
        initial_sample = parse_sample(
            INPUT_SAMPLE_ARCHIVE, entry["parameters"]["args"]["initial_sample_path"]
        )
        for conf in initial_sample:
            conf["__Root__"] = True
            assert instance.is_feasible(conf, verbose=True)
        for conf in lns_sample:
            conf["__Root__"] = True
            assert instance.is_feasible(conf, verbose=True)
        if have_equal_coverage(instance, lns_sample, initial_sample):
            data_.append(entry)
        else:
            raise AssertionError()
