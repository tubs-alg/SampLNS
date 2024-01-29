from pathlib import Path
from zipfile import ZipFile
import subprocess


INSTANCES = [
    "calculate",
    "lcm",
    "email",
    "ChatClient",
    "car",
    "FeatureIDE",
    "FameDB2",
    "FameDB",
    "APL",
    "SafeBali",
    "APL-Model",
    "gpl",
    "dell",
    "PPU",
    "fiasco",
    "berkeleyDB1",
    "axTLS",
    "berkeleyDB2",
    "BattleofTanks",
    "BankingSoftware",
    "eShopSplot",
    "E-Shop",
    "eShopFIDE",
    "DMIE",
    "fs_2017-05-22",
    "financial_services",
    "busybox-1_18_0",
    "busybox-1_23_1",
    "busybox-1_29_2",
    "am31_sim",
    "EMBToolkit",
    "calm16_ceb",
    "calm32_ceb",
    "psim",
    "h8300h_sim",
    "h8s_sim",
    "fads",
    "ceb_v850",
    "edosk2674",
    "jmr3904",
    "h8max",
    "cma28x",
    "aki3068net",
    "atlas_mips64_5kc",
    "cma230",
    "mpc50",
    "gps4020",
    "aeb",
    "atlas_mips32_4kc",
    "ref4955",
    "brutus",
    "sa1100mm",
    "prpmc1100",
    "pid",
    "mb93093",
    "asb",
    "malta_mips64_5kc",
    "malta_mips32_4kc",
    "eCos-3-0_i386pc",
    "csb281",
    "eb42",
    "mac7100evb",
    "mace1",
    "excalibur_arm9",
    "frv400",
    "cq7708",
    "eb40",
    "grg",
    "eb40a",
    "jtst",
    "asb2305",
    "ebsa285",
    "edb7xxx",
    "ixdp425",
    "pati",
    "picasso",
    "lpcmt",
    "p2106",
    "mcb2100",
    "mb93091",
    "dreamcast",
    "sh7708",
    "pc_vmWare",
    "iq80321",
    "innovator",
    "pc_rltk8139",
    "iq80310",
    "npwr",
    "ipaq",
    "pc_i82544",
    "pc_i82559",
    "integrator_arm7",
    "sh4_202_md",
    "olpch2294",
    "refidt334",
    "aim711",
    "nano",
    "flexanet",
    "ocelot",
    "cme555",
    "assabet",
    "e7t",
    "ec555",
    "cq7750",
    "integrator_arm9",
    "eb55",
    "adder",
    "olpcl2294",
    "phycore",
    "olpce2294",
    "cerf",
    "adderII",
    "moab",
    "pc_usb_d12",
    "aaed2000",
    "cerfpda",
    "mbx",
    "se7751",
    "at91sam7sek",
    "hs7729pci",
    "rattler",
    "at91sam7xek",
    "se77x9",
    "m5272c3",
    "sam7ex256",
    "phycore229x",
    "FreeBSD-8_0_0",
    "ea2468",
    "toybox_2006-10-31_23-30-06",
    "TightVNC",
    "SortingLine",
    "Violet",
    "soletta_2015-06-26_18-38-56",
    "fiasco_2017-09-26_11-30-56",
    "fiasco_2020-12-01_14-09-14",
    "uclibc_2008-06-05_13-46-47",
    "uclibc_2020-12-24_11-54-53",
    "toybox_2020-12-06_00-02-46",
    "soletta_2017-03-09_21-02-40",
    "busybox_2007-01-24_09-14-09",
    "WaterlooGenerated",
    "busybox_2020-12-16_21-53-05",
    "XSEngine",
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
def run_yasa(instance_name: str, output: str, timeout: int) -> None:
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
        ],
        capture_output=False,
        check=True,
    )
    runner.check_returncode()


if __name__ == "__main__":
    Path("./results").mkdir(exist_ok=True)
    for instance in INSTANCES:
        Path(f"./results/{instance}").mkdir(exist_ok=True)
        for rep in range(0, 5):
            run_yasa.distribute(instance, f"./results/{instance}/sample_{rep}.csv", 900)

