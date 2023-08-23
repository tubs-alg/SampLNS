import logging
import os
import shutil
import subprocess
import sys
import tempfile
from glob import glob

import pandas as pd

_logger = logging.getLogger("SampLNS")


class BaselineAlgorithm:
    """
    Provides an interface for running baseline algorithms with FeatJAR
    """

    DEFAULT_CONFIGURATION = {
        "output": "results",
        "models": "models",
        "phases": "clean,de.featjar.evaluation.twise.SamplingPhase",
        "seed": 1,
        "timeout": 0,
        "systemIterations": 1,
        "algorithmIterations": 1,
        "verbosity": 0,
        "algorithm": "",
        "t": 2,
    }

    def __init__(
        self, file_path: str, algorithm="YASA", logger: logging.Logger = _logger
    ):
        self._configuration = self.DEFAULT_CONFIGURATION.copy()
        self._configuration_dir = "config"
        self._model_path = file_path
        self._jars_dir = os.path.join(sys.prefix, "deps/samplns")
        self._log = logger.getChild("Baseline")

        if algorithm == "YASA":
            self._configuration["algorithm"] = "YA"
        elif algorithm == "YASA3":
            self._configuration["algorithm"] = "YA3"
        elif algorithm == "YASA5":
            self._configuration["algorithm"] = "YA5"
        elif algorithm == "YASA10":
            self._configuration["algorithm"] = "YA10"
        else:
            msg = "Unknown algorithm"
            raise ValueError(msg)

        assert os.path.isfile(self._model_path)

    def _prepare(self, tmp_dir):
        """
        The sampling jar expects a configuration and models folder. Also the tools dir has to be linked to the
        experiment dir
        @param tmp_dir Temporary directory in which the solving process should be prepared
        """

        model_name = "model"

        config_dir = os.path.join(tmp_dir, self._configuration_dir)
        model_dir = os.path.join(tmp_dir, self._configuration["models"], model_name)
        os.makedirs(config_dir)
        os.makedirs(model_dir)

        config_file = os.path.join(config_dir, "config.properties")
        model_file = os.path.join(config_dir, "models.txt")
        with open(config_file, "w") as f:
            for key, val in self._configuration.items():
                f.write(f"{key}={val}\n")

        with open(model_file, "w") as f:
            f.write("model\n")

        shutil.copy(
            self._model_path,
            os.path.join(model_dir, os.path.basename(self._model_path)),
        )
        os.symlink(
            os.path.join(self._jars_dir, "tools"), os.path.join(tmp_dir, "tools")
        )

    def _parse_result(self, tmp_dir):
        # This matches all valid samples that were generated.
        samples = glob(
            os.path.join(tmp_dir, self._configuration["output"], "*", "*.csv")
        )

        if not samples:
            return None

        assert len(samples) > 0

        t = pd.read_csv(samples[0], sep=";", index_col="Configuration")
        samples = []
        t.apply(
            lambda row: samples.append({k: v == "+" for k, v in row.items()}), axis=1
        )
        return samples

    def optimize(self, timelimit):
        """
        Uses some FeatJAR baseline algorithm to solve the given instance.
        @param timelimit Time limit in seconds
        """
        self._configuration["timeout"] = (
            timelimit * 1000
        )  # convert seconds to milliseconds

        with tempfile.TemporaryDirectory() as tmp_dir:
            self._log.info(f"Created temporary directory {tmp_dir}")
            self._prepare(tmp_dir)

            runner = subprocess.run(
                [
                    "java",
                    "-jar",
                    os.path.join(
                        self._jars_dir,
                        "evaluation-sampling-algorithms-0.1.0-SNAPSHOT-all.jar",
                    ),
                    "twise-sampler",
                    self._configuration_dir,
                ],
                cwd=tmp_dir,
                capture_output=True,
                text=True,
            )
            self._log.info(runner.stdout)
            self._log.error(runner.stderr)

            self._log.info("Finished running baseline. Parsing result...")

            samples = self._parse_result(tmp_dir)

            if samples:
                self._log.info("Found a valid sample.")

        return samples
