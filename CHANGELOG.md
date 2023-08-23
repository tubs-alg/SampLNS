- _2023-08-07 (DK):_ Created changelog
- _2023-08-07 (DK):_ Extended error message when parsing DIMACS files and a
  feature is named multiple times. Note that we still expect the comments to be
  a specific format, which is actually not defined this way. We should think
  about just using the indices and hoping that the solution files follow the
  same order. The reason for extracting the variable names from the comments is
  that the solution files use the names, not the indices. However, I would
  expect them to follow the same order. Generally, we should improve the error
  messages and the checking in the parser and stuff as this is critical and also
  exposed to the end user.
- _2023-08-08 (GG):_ Removed the experimental, unfinished, and abandoned genetic
  CDS algorithm.
- _2023-08-08 (GG):_ Merged the new C++ logger from its dev branch into main.
  (Currently unused, will be used in the future)
- _2023-08-08 (GG):_ Extended the CdsAlgorithm interface: Added option to set a
  time limit for independent tuple computation. Added option to provide
  CdsAlgorithm with known upper bound (e.g. for LNS neighborhoods), such that
  computation can be interrupted when the upper bound is met.
- _2023-08-20 (DK):_ Added CDS iteration time limit to top level interface (was
  fixed to 60s) and returning the initial set if CDS cannot compute any feasible
  solution.
