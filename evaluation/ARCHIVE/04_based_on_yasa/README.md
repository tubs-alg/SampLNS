# Experiments based on YASA m=1

*Created 2023-08-07 by Dominik Krupke*

Reviewer complained that SampLNS is not stand-alone.
This experiment acts like it is stand-alone, using YASA(m=1) as a subroutine.
The solutions of YASA(m=1) are actually precomputed but the time limits, etc., are adapted as if it was integrated.

These experiments also use the improved version of SampLNS, which can optimize larger instances.
The performance of the lower bound procedure seems to have deteriorated, though.
We have to check that. This may be due to a bug that was not nicely patched (just returning an empty lb on timeout).

**Outdated. Go for 06_cds_improvments instead.**