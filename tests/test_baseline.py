import os
import subprocess
import tempfile

from samplns.baseline import BaselineAlgorithm


def test_java():
    runner = subprocess.run("java --version", capture_output=True, shell=True)
    assert runner.returncode == 0, (
        "It seems like Java was not installed on your system. "
        "FeatJAR requires at least Java 11."
    )


def test_yasa():
    toybox_instance_xml = '<?xml version="1.0" encoding="UTF-8" standalone="no"?> <featureModel> <properties/> <struct> <and abstract="true" mandatory="true" name="__Root__"> <feature name="CONFIG_CONFIG_DF"/> <feature name="CONFIG_CONFIG_DF_PEDANTIC"/> <feature name="CONFIG_CONFIG_TOYSH_TTY"/> <feature name="CONFIG_CONFIG_TOYSH_PROFILE"/> <feature name="CONFIG_CONFIG_TOYSH_ENVVARS"/> <feature name="CONFIG_CONFIG_TOYSH_LOCALS"/> <feature name="CONFIG_CONFIG_TOYSH_BUILTINS"/> <feature name="CONFIG_CONFIG_TOYSH"/> <feature name="CONFIG_CONFIG_TOYSH_JOBCTL"/> <feature name="CONFIG_CONFIG_TOYSH_ARRAYS"/> <feature name="CONFIG_CONFIG_TOYSH_PIPES"/> <feature name="CONFIG_CONFIG_TOYSH_QUOTES"/> <feature name="CONFIG_CONFIG_TOYSH_WILDCARDS"/> <feature name="CONFIG_CONFIG_TOYSH_PROCARGS"/> <feature name="CONFIG_CONFIG_TOYSH_FLOWCTL"/> </and> </struct> <constraints> <rule> <disj> <var>CONFIG_CONFIG_DF</var> <not> <var>CONFIG_CONFIG_DF_PEDANTIC</var> </not> </disj> </rule> <rule> <disj> <var>CONFIG_CONFIG_TOYSH_TTY</var> <not> <var>CONFIG_CONFIG_TOYSH_PROFILE</var> </not> </disj> </rule> <rule> <disj> <var>CONFIG_CONFIG_TOYSH_ENVVARS</var> <not> <var>CONFIG_CONFIG_TOYSH_LOCALS</var> </not> </disj> </rule> <rule> <disj> <not> <var>CONFIG_CONFIG_TOYSH_BUILTINS</var> </not> <var>CONFIG_CONFIG_TOYSH</var> </disj> </rule> <rule> <disj> <var>CONFIG_CONFIG_TOYSH_TTY</var> <not> <var>CONFIG_CONFIG_TOYSH_JOBCTL</var> </not> </disj> </rule> <rule> <disj> <not> <var>CONFIG_CONFIG_TOYSH_ARRAYS</var> </not> <var>CONFIG_CONFIG_TOYSH_LOCALS</var> </disj> </rule> <rule> <disj> <not> <var>CONFIG_CONFIG_TOYSH_PIPES</var> </not> <var>CONFIG_CONFIG_TOYSH</var> </disj> </rule> <rule> <disj> <not> <var>CONFIG_CONFIG_TOYSH_TTY</var> </not> <var>CONFIG_CONFIG_TOYSH</var> </disj> </rule> <rule> <disj> <not> <var>CONFIG_CONFIG_TOYSH_ENVVARS</var> </not> <var>CONFIG_CONFIG_TOYSH_QUOTES</var> </disj> </rule> <rule> <disj> <not> <var>CONFIG_CONFIG_TOYSH_WILDCARDS</var> </not> <var>CONFIG_CONFIG_TOYSH_QUOTES</var> </disj> </rule> <rule> <disj> <not> <var>CONFIG_CONFIG_TOYSH_QUOTES</var> </not> <var>CONFIG_CONFIG_TOYSH</var> </disj> </rule> <rule> <disj> <not> <var>CONFIG_CONFIG_TOYSH_PROCARGS</var> </not> <var>CONFIG_CONFIG_TOYSH_QUOTES</var> </disj> </rule> <rule> <disj> <not> <var>CONFIG_CONFIG_TOYSH_FLOWCTL</var> </not> <var>CONFIG_CONFIG_TOYSH</var> </disj> </rule> </constraints> <calculations Auto="true" Constraints="true" Features="true" Redundant="true" Tautology="true"/> <comments/> <featureOrder userDefined="false"/> </featureModel>'

    for algorithm in ["YASA", "YASA3", "YASA5", "YASA10"]:
        with tempfile.TemporaryDirectory() as tmp_dir:
            instance_file = os.path.join(tmp_dir, "model.xml")
            with open(instance_file, "w") as f:
                f.write(toybox_instance_xml)

            baseline = BaselineAlgorithm(instance_file, algorithm=algorithm)
            sample = baseline.optimize(10)

            assert sample is not None
            assert len(sample) > 0
