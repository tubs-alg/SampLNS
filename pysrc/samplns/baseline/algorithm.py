import logging
import os
import random
import shutil
import subprocess
import sys
import tempfile
from glob import glob
from pathlib import Path
from typing import Optional

import pandas as pd

_logger = logging.getLogger("SampLNS")

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

class BaselineAlgorithm:
    """
    Provides an interface for running baseline algorithms with FeatJAR
    """

    def __init__(
        self,
        file_path: str,
        algorithm="YASA",
        logger: logging.Logger = _logger,
        seed: Optional[int] = None,
        jars_dir: str|None = None,
    ):
        self._configuration = DEFAULT_CONFIGURATION.copy()
        if seed is not None:
            self._configuration["seed"] = seed
        else:
            self._configuration["seed"] = random.randint(0, 2**31 - 1)

        self._configuration_dir = "config"
        self._model_path = file_path
        if jars_dir is not None:
            self._jars_dir = jars_dir
        else:
            self._jars_dir = os.path.join(sys.prefix, "deps/samplns")
        self._log = logger.getChild("Baseline")
        self._log.info("Using seed %d for FeatureIDE", self._configuration["seed"])

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
        if Path(self._model_path).is_dir():
            # check for a `model.dimacs` or `model.xml` file in the given directory.
            if Path(self._model_path, "model.xml").is_file():  # always prefer xml as it is more expressive
                self._model_path = str(Path(self._model_path) / "model.xml")
            elif Path(self._model_path, "model.dimacs").is_file():
                self._model_path = str(Path(self._model_path) / "model.dimacs")
            else:
                msg = f"The given model path '{self._model_path}' is a directory, but does not contain a model.dimacs or model.xml file."
                raise ValueError(msg)
        if not Path(self._model_path).is_file():
            msg = f"The given model path '{self._model_path}' is not a valid file."
            raise ValueError(msg)

    def _prepare(self, tmp_dir):
        """
        The sampling jar expects a configuration and models folder. Also the tools dir has to be linked to the
        experiment dir
        @param tmp_dir Temporary directory in which the solving process should be prepared
        """

        model_name = "model"

        config_dir = Path(tmp_dir) / self._configuration_dir
        model_dir = Path(tmp_dir) / self._configuration["models"] / model_name
        config_dir.mkdir(parents=True, exist_ok=True)
        model_dir.mkdir(parents=True, exist_ok=True)

        config_file = config_dir / "config.properties"
        model_file = config_dir / "models.txt"
        with config_file.open("w") as f:
            for key, val in self._configuration.items():
                f.write(f"{key}={val}\n")

        with model_file.open("w") as f:
            f.write("model\n")

        input_suffix = self._model_path.split(".")[-1].lower()
        if input_suffix not in ["dimacs", "xml"]:
            msg = f"The given model path '{self._model_path}' does not point to a .dimacs or .xml file."
            raise ValueError(msg)
        model_dst = model_dir / f"model.{input_suffix}"
        self._log.info("Copying model from %s to %s for solving with FeatureIDE", self._model_path, model_dst)
        shutil.copy(
            self._model_path,
            dst=model_dst,
        )
        os.symlink(
            Path(self._jars_dir) / "tools", Path(tmp_dir) / "tools"
        )

    def _parse_result(self, tmp_dir):
        # This matches all valid samples that were generated.
        samples = list((Path(tmp_dir) / self._configuration["output"]).glob("*/*.csv"))

        if not samples:
            logging.error("The folder %s contains no samples. Content: %s", tmp_dir, str(os.listdir(tmp_dir)))
            return None

        if len(samples) == 0:
            msg = "No sample found. This should not happen."
            raise ValueError(msg)

        t = pd.read_csv(samples[0], sep=";", index_col="Configuration")
        samples = []
        t.apply(
            lambda row: samples.append({k: v == "+" for k, v in row.items()}), axis=1
        )
        return samples

    def optimize(self, timelimit: float) -> list[dict]|None:
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
                    Path(self._jars_dir) / "evaluation-sampling-algorithms-0.1.0-SNAPSHOT-all.jar",
                    "twise-sampler",
                    self._configuration_dir,
                ],
                cwd=tmp_dir,
                capture_output=True,
                text=True,
                check=False,
            )
            self._log.info("stdout from featureide: %s", runner.stdout)
            self._log.error("stderr from featureide: %s", runner.stderr)

            self._log.info("Finished running baseline. Parsing result...")

            samples = self._parse_result(tmp_dir)

            if samples:
                self._log.info("Found a valid sample.")
            else:
                self._log.info("No valid sample found. Files in %s: %s", tmp_dir, str(os.listdir(tmp_dir)))

        return samples
