# How to obtain the FeatJar evaluation JAR

In order to obtain the jar file (in case it needs to be rebuild at some point)
run the following commands:

```
git clone --branch evaluation_sampling_algorithms git@github.com:FeatureIDE/FeatJAR.git
cd FeatJAR
./setup.sh
```

This will build and download all dependencies and output the sampling JARs into
`FeatJAR/evaluation-sampling-algorithms/build/libs/` and
`FeatJAR/evaluation-sampling-algorithms/tools`.
