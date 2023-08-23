- _2023-08-07 (DK):_ Created changelog to keep track of all changes and
  problems.
- _2023-08-07 (DK):_ The instance `soletta_2017-03-09_21-02-40` reuses a
  variable name. It is in dimacs format. This could be solved by using the
  indices instead of the variable names, as they are actually just comments.
  However, the solutions uses the variable names, too, and we would have to
  trust that the order is the same. We should think about this.
- _2023-08-07 (DK):_ Experiments completed on AlgRys. Ready for evaluation.
  However, the notebooks which just have been copied from the previous
  evaluations still have to be adapted.
- _2023-08-07 (DK):_ Did the first evaluation. Data still looks good, the
  optimality gap is more than halved on average. Even if the lower bounds got
  worse, our results are still good. The better the lower bounds would get, get
  the better our results would actually become. However, we miss out on number
  of instance solved to optimality.
