from pathlib import Path
from zipfile import ZipFile
import subprocess
import tomllib

with (Path(__file__).parent/".."/"config.toml").open("rb") as f:
        config = tomllib.load(f)
        config_exp = config[Path(__file__).parent.name]
INSTANCES = config["benchmark"]["instance_names"]


import slurminade

# ================================================
# SLURM CONFIGURATION FOR DISTRIBUTED EXECUTION
# ------------------------------------------------
slurminade.update_default_configuration(
    partition="alg",
    constraint="alggen05",
    mail_user="krupke@ibr.cs.tu-bs.de",
    mail_type="FAIL",
    exclusive=True,
)
slurminade.set_dispatch_limit(300)


def prepare_instance(instance_name: str) -> Path:
    """
    Extract an instance file from the archive and return its path.
    """
    instance_archive = Path("..") / config["benchmark"]["instance_archive"]
    path_in_zip_xml = Path("models") / instance_name / Path("model.xml")
    path_in_zip_dimacs = Path("models") / instance_name / Path("model.dimacs")

    if instance_archive.is_file():
        with ZipFile(instance_archive) as zf:

            def exists(path: Path) -> bool:
                return str(path) in zf.namelist()

            # throw exception if both files exist -> ambiguous
            if exists(path_in_zip_xml) and exists(path_in_zip_dimacs):
                raise RuntimeError(
                    f"Ambiguous: {path_in_zip_xml} and {path_in_zip_dimacs} found in {instance_archive}"
                )
            elif exists(path_in_zip_xml):
                if not path_in_zip_xml.exists():
                    print(f"Extracting {path_in_zip_xml} from {instance_archive}")
                    zf.extract(str(path_in_zip_xml))
                return path_in_zip_xml
            elif exists(path_in_zip_dimacs):
                if not path_in_zip_dimacs.exists():
                    print(f"Extracting {path_in_zip_dimacs} from {instance_archive}")
                    zf.extract(str(path_in_zip_dimacs))
                return path_in_zip_dimacs
            else:
                raise FileNotFoundError(
                    f"Neither {path_in_zip_xml} nor {path_in_zip_dimacs} found in {instance_archive}"
                )
    else:
        raise FileNotFoundError(f"{instance_archive} not found")


@slurminade.slurmify
def run_yasa(instance_name: str, output: str, timeout: int, seed: int) -> None:
        """
    Run YASA on an instance and return the time used.

    java -jar formula-analysis-sat4j-0.1.1-SNAPSHOT-all.jar --command de.featjar.formula.analysis.cli.TWiseCommand --input model.xml --output sample.csv --t 2 --i -1 --timeout 100
    """
        if Path(output).exists():
            print(f"Skipping {instance_name} because {output} exists")
            return
        instance_path = prepare_instance(instance_name)
        runner = subprocess.run(
            [
                "java",
                "-jar",
                "formula-analysis-sat4j-0.1.1-SNAPSHOT-all.jar",
                "--command",
                "de.featjar.formula.analysis.cli.TWiseCommand",
                "--input",
                str(instance_path),
                "--output",
                output,
                "--t",
                "2",
                "--i",
                "-1",
                "--timeout",
                str(timeout),
                "--seed",
                str(seed),
            ],
            capture_output=False,
            check=True,
        )
        runner.check_returncode()


if __name__ == "__main__":
    if not Path("formula-analysis-sat4j-0.1.1-SNAPSHOT-all.jar").exists():
        raise RuntimeError(
            "Please put formula-analysis-sat4j-0.1.1-SNAPSHOT-all.jar in this folder."
        )
    Path(config_exp["result_folder"]).mkdir(exist_ok=True)
    for rep in range(5):
        for instance in INSTANCES:
            Path(f"./{config_exp['result_folder']}/{instance}").mkdir(exist_ok=True)
            result_path = Path(f"./{config_exp['result_folder']}/{instance}/sample_{rep}.csv")
            if result_path.exists():
                print(f"Skipping {instance} because {result_path} exists")
                continue
            run_yasa.distribute(instance, str(result_path), 900, rep)
