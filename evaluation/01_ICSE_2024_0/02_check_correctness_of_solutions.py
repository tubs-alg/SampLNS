from _utils import get_instance, parse_sample
from aemeasure import Database
from samplns.verify import have_equal_coverage

TIME_LIMIT = 900
BASE = "900_seconds_5_it"
INPUT_SAMPLE_ARCHIVE = f"./00_baseline/{BASE}.zip"
INSTANCE_ARCHIVE = "./00_benchmark_instances.zip"
RESULT_FOLDER = f"01_results/{BASE}_{TIME_LIMIT}"

if __name__ == "__main__":
    data = Database(RESULT_FOLDER).load()
    data_ = []
    for entry in data:
        instance = get_instance(entry["instance"], INSTANCE_ARCHIVE)
        lns_sample = entry["solution"]
        initial_sample = parse_sample(
            INPUT_SAMPLE_ARCHIVE, entry["initial_sample_path"]
        )
        if have_equal_coverage(instance, lns_sample, initial_sample):
            data_.append(entry)
        else:
            raise AssertionError()
