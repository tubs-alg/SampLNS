======================
SampLNS Documentation
======================

Welcome to SampLNS's documentation!
This documentation is intended for developers who want to use SampLNS in their own projects.
If you have any questions, please write a GitHub issue.


SampLNS is an LNS-based optimizer for pairwise configuration sampling
that comes with a lower bound proving technique. On many of the
instances we tested, it is able to compute smaller samples than YASA and
frequently to even prove optimality. A paper describing the approach is
currently in progress.

.. note::
    The implementation is for research purposes only and not yet ready for production. Please contact us if you want to use it in production.

The general idea of SampLNS is as follows: Theoretically, the problem of
finding a minimal can be expressed as a SAT-problem. However, this is
not feasible in practice as the formula is way too large. If we have an
initial sample, we can use it to fix a part of the formula and then
solve the remaining, much smaller, formula. If we repeat this process
multiple times, we have a good chance of finding a minimal sample. This
is essentially a Large Neighborhood Search (LNS). To break symmetries in
the formula and supply the LNS with a lower bound, we have an additional
optimizer that searches for a large set of mutually exclusive pairs of
features.

**What is a Large Neighborhood Search (LNS)?** It is a metaheuristic for
optimization problems that works as follows: You start with a feasible
solution. Then, you iteratively destroy a part if the solution and try
to repair it in a way that improves the solution. We are using Mixed
Integer Programming and a SAT-based approach to do so, which allows us
to find optimal solutions for the repair step. Mixed Integer Programming
is a powerful technique that can solve many NP-hard problems optimally
up to a reasonable size. The size of the destroyed part is scaled
automatically to be as large as possible while still being able to find
a repair. The larger the destroyed part, the more likely it is to escape
local minima and find an even better solution, potentially even an
optimal solution. As the candidate set of improvements is implicitly
defined by an optimization problem, we do not have to iterate over all
possible improvements as simple local search strategies have to. This
allows us to consider a significantly larger number of improvements,
which significantly increases the chance of finding a good solution. The
downside is that we have to solve an optimization problem for each
improvement, which is computationally expensive and limits scalability.

**What is a lower bound and why is it useful?** A lower bound is a value
that is guaranteed to be smaller than the optimal solution. If you have
a lower bound, you can stop the optimization process as soon as you
reach it. The lower bound proves that you cannot find a better solution.
If the optimization process is not able to match it, the lower bound at
least gives you a guaranteed upper bound on the error of your solution.
Computing perfect lower bounds for NP-hard problems is itself NP-hard,
so we are only able to approximate them. However, every lower bound
returned is still guaranteed to be smaller than the optimal solution. It
may just not be sufficient to prove optimality.

**Why does SampLNS not compute its own initial samples?** SampLNS
requires an initial sample to start the optimization process. We do not
compute this initial sample ourselves, but require the user to provide
it. This is because there are already many good tools for computing
initial samples, such as `FeatureIDE <https://featureide.github.io/>`__.
We do not want to reinvent the wheel and instead focus on the
optimization process. If you do not have an initial solution, you can
use the `FeatureIDE <https://featureide.github.io/>`__ to compute one.

.. toctree::
   :maxdepth: 2
   :caption: SampLNS Documentation:

   install
   modules
