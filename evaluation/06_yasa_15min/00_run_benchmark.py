import subprocess
from pathlib import Path
from zipfile import ZipFile

INSTANCES = [
    "calculate",
    "lcm",
    "email",
    "ChatClient",
    "toybox_2006-10-31_23-30-06",
    "car",
    "FeatureIDE",
    "FameDB",
    "APL",
    "SafeBali",
    "TightVNC",
    "APL-Model",
    "gpl",
    "SortingLine",
    "dell",
    "PPU",
    "berkeleyDB1",
    "axTLS",
    "Violet",
    "berkeleyDB2",
    "soletta_2015-06-26_18-38-56",
    "BattleofTanks",
    "BankingSoftware",
    "fiasco_2017-09-26_11-30-56",
    "fiasco_2020-12-01_14-09-14",
    "uclibc_2008-06-05_13-46-47",
    "uclibc_2020-12-24_11-54-53",
    "E-Shop",
    "toybox_2020-12-06_00-02-46",
    "DMIE",
    "soletta_2017-03-09_21-02-40",
    "busybox_2007-01-24_09-14-09",
    "fs_2017-05-22",
    "WaterlooGenerated",
    "financial_services",
    "busybox-1_18_0",
    "busybox-1_29_2",
    "busybox_2020-12-16_21-53-05",
    "am31_sim",
    "EMBToolkit",
    "atlas_mips32_4kc",
    "eCos-3-0_i386pc",
    "integrator_arm7",
    "XSEngine",
    "aaed2000",
    "FreeBSD-8_0_0",
    "ea2468",
    "Automotive01",
    "main_light",
    "freetz",
]

import slurminade

# ================================================
# SLURM CONFIGURATION FOR DISTRIBUTED EXECUTION
# ------------------------------------------------
slurminade.update_default_configuration(
    partition="alg",
    constraint="alggen03",
    mail_user="krupke@ibr.cs.tu-bs.de",
    mail_type="FAIL",
)
slurminade.set_dispatch_limit(300)


def prepare_instance(instance_name: str) -> Path:
    """
    Extract an instance file from the archive and return its path.
    """
    instance_archive = Path("../benchmark_models.zip")
    path_in_zip_xml = Path("models") / instance_name / Path("model.xml")
    path_in_zip_dimacs = Path("models") / instance_name / Path("model.dimacs")

    if instance_archive.is_file():
        with ZipFile(instance_archive) as zf:

            def exists(path: Path) -> bool:
                return str(path) in zf.namelist()

            # throw exception if both files exist -> ambiguous
            if exists(path_in_zip_xml) and exists(path_in_zip_dimacs):
                msg = f"Ambiguous: {path_in_zip_xml} and {path_in_zip_dimacs} found in {instance_archive}"
                raise RuntimeError(
                    msg
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
                msg = f"Neither {path_in_zip_xml} nor {path_in_zip_dimacs} found in {instance_archive}"
                raise FileNotFoundError(
                    msg
                )
    else:
        msg = f"{instance_archive} not found"
        raise FileNotFoundError(msg)


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
            str(output),
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
        msg = "Please put formula-analysis-sat4j-0.1.1-SNAPSHOT-all.jar in this folder."
        raise RuntimeError(
            msg
        )
    Path("./results").mkdir(exist_ok=True)
    for rep in range(0, 5):
        for instance in INSTANCES:
            Path(f"./results/{instance}").mkdir(exist_ok=True)
            result_path = Path(f"./results/{instance}/sample_{rep}.csv")
            if result_path.exists():
                print(f"Skipping {instance} because {result_path} exists")
                continue
            run_yasa.distribute(instance, str(result_path), 900, rep)
