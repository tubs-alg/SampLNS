# SampLNS: A Large Neighborhood Search to compute near minimal samples for feature models

SampLNS is an LNS-based optimizer for pairwise configuration sampling that comes
with a lower bound proving technique. On many of the instances we tested, it is
able to compute smaller samples than YASA and frequently to even prove
optimality. A paper describing the approach is currently in progress.

> :warning: The implementation is for research purposes only and not yet ready
> for production. Please contact us if you want to use it in production.

The general idea of SampLNS is as follows: Theoretically, the problem of finding
a minimal can be expressed as a SAT-problem. However, this is not feasible in
practice as the formula is way too large. If we have an initial sample, we can
use it to fix a part of the formula and then solve the remaining, much smaller,
formula. If we repeat this process multiple times, we have a good chance of
finding a minimal sample. This is essentially a Large Neighborhood Search (LNS).
To break symmetries in the formula and supply the LNS with a lower bound, we
have an additional optimizer that searches for a large set of mutually exclusive
pairs of features.

**What is a Large Neighborhood Search (LNS)?** It is a metaheuristic for
optimization problems that works as follows: You start with a feasible solution.
Then, you iteratively destroy a part if the solution and try to repair it in a
way that improves the solution. We are using Mixed Integer Programming and a
SAT-based approach to do so, which allows us to find optimal solutions for the
repair step. Mixed Integer Programming is a powerful technique that can solve
many NP-hard problems optimally up to a reasonable size. The size of the
destroyed part is scaled automatically to be as large as possible while still
being able to find a repair. The larger the destroyed part, the more likely it
is to escape local minima and find an even better solution, potentially even an
optimal solution. As the candidate set of improvements is implicitly defined by
an optimization problem, we do not have to iterate over all possible
improvements as simple local search strategies have to. This allows us to
consider a significantly larger number of improvements, which significantly
increases the chance of finding a good solution. The downside is that we have to
solve an optimization problem for each improvement, which is computationally
expensive and limits scalability.

**What is a lower bound and why is it useful?** A lower bound is a value that is
guaranteed to be smaller than the optimal solution. If you have a lower bound,
you can stop the optimization process as soon as you reach it. The lower bound
proves that you cannot find a better solution. If the optimization process is
not able to match it, the lower bound at least gives you a guaranteed upper
bound on the error of your solution. Computing perfect lower bounds for NP-hard
problems is itself NP-hard, so we are only able to approximate them. However,
every lower bound returned is still guaranteed to be smaller than the optimal
solution. It may just not be sufficient to prove optimality.

**Why does SampLNS not compute its own initial samples?** SampLNS requires an
initial sample to start the optimization process. We do not compute this initial
sample ourselves, but require the user to provide it. This is because there are
already many good tools for computing initial samples, such as
[FeatureIDE](https://featureide.github.io/). We do not want to reinvent the
wheel and instead focus on the optimization process. If you do not have an
initial solution, you can use the [FeatureIDE](https://featureide.github.io/) to
compute one.

## Installation

This package requires a valid license of the commercial MIP-solver Gurobi. You
can get a free license for academic purposes. These academic licenses are fairly
easy to obtain, as explained in
[this video](https://www.youtube.com/watch?v=oW6ma8rdZk8):

1. Register an academic account.
2. Install Gurobi (very easy with Conda, you only need the tool `grbgetkey`).
3. Use `grbgetkey` to set up a license on your computer. You may have to be
   within the university network for this to work.

After you got your license, move into the folder with `setup.py` and run

```shell
pip install .
```

This command should automatically install all dependencies and build the
package. The package contains native C++-code that is compiled during
installation. This requires a C++-compiler. On most systems, this should be
installed by default. If not, you can install it via

```shell
sudo apt install build-essential  # Ubuntu
sudo pacman -S base-devel         # Arch
```

If you don't have initial samples at hand you might want to generate initial
samples for SampLNS with FeatJAR. This requires you to install Java version 11
or higher.

```shell
sudo apt-get install openjdk-11-jdk
```

Generally, the installation will take a while as it has to compile the C++, but
it should work out of the box. If you encounter any problems, please open an
issue. Unfortunately, the performance of native code is bought with a more
complex installation process, and it is difficult to make it work on all
systems. Windows systems are especially difficult to support. We suggest using a
Linux system.

## Usage

We provide a CLI and a Python interface. The CLI is the easiest way to get
started. If you have an initial sample you can use it as follows:

```shell
samplns -f <path/to/model> --initial-sample <path/to/intial/sample>
```

If you do not have an initial sample, you can use the following command to
compute one with YASA:

```shell
samplns -f <path/to/model> --initial-sample-algorithm YASA
```

For further options see help:

```shell
samplns --help
usage: samplns [-h] -f FILE [-o OUTPUT] (--initial-sample INITIAL_SAMPLE | --initial-sample-algorithm {YASA,YASA3,YASA5,YASA10}) [--initial-sample-algorithm-timelimit INITIAL_SAMPLE_ALGORITHM_TIMELIMIT] [--samplns-timelimit SAMPLNS_TIMELIMIT] [--samplns-max-iterations SAMPLNS_MAX_ITERATIONS] [--samplns-iteration-timelimit SAMPLNS_ITERATION_TIMELIMIT] [--cds-iteration-timelimit CDS_ITERATION_TIMELIMIT]

Starts samplns either with a given initial sample or runs another sampling algorithm before.

options:
  -h, --help            show this help message and exit
  -f FILE, --file FILE  File path to the instance (either FeatJAR xml or DIMACS format.)
  -o OUTPUT, --output OUTPUT
                        File path to the output file. Default: sample.json
  --initial-sample INITIAL_SAMPLE
                        Set this when you already have an initial sample. File path to an initial sample (JSON) that should be used.
  --initial-sample-algorithm {YASA,YASA3,YASA5,YASA10}
                        Set this if you want to run a sampling algorithm to generate an initial sample. YASA has several versions for different values of m.
  --initial-sample-algorithm-timelimit INITIAL_SAMPLE_ALGORITHM_TIMELIMIT
                        Timelimit of the initial sampling algorithm in seconds.
  --samplns-timelimit SAMPLNS_TIMELIMIT
                        Timelimit of samplns in seconds.
  --samplns-max-iterations SAMPLNS_MAX_ITERATIONS
                        Maximum number of iterations for samplns.
  --samplns-iteration-timelimit SAMPLNS_ITERATION_TIMELIMIT
                        Timelimit for each iteration of samplns in seconds.
  --cds-iteration-timelimit CDS_ITERATION_TIMELIMIT
                        Timelimit for each iteration of the lower bound computation in seconds.
```

If you want to use the Python interface, you can check out the following example
from `examples/`:

```python
import json

from samplns.simple import SampLns
from samplns.instances import parse

if __name__ == "__main__":
    feature_model = parse("./toybox_2006-10-31_23-30-06/model.xml")
    with open("./yasa_sample.json") as f:
        initial_sample = json.load(f)
    solver = SampLns(
        instance=feature_model,
        initial_solution=initial_sample,
    )

    solver.optimize(
        iterations=10000,
        iteration_timelimit=60.0,
        timelimit=900,
    )
    optimized_sample = solver.get_best_solution(verify=True)
    print(
        f"Reduced initial sample of size {len(initial_sample)} to {len(optimized_sample)}"
    )
    print(f"Proved lower bound is {solver.get_lower_bound()}.")
```

> ! The samples have to be lists of fully defined dictionaries. Otherwise, the
> results may be wrong. We will add automatic warnings for that soon.

## Logging

The optimizer uses the Python logging module. You can configure it as you like.
The default logger is named "SampLNS" and does not print anything. You can
change the logging level by adding the following lines to your code:

```python
import logging

logging.getLogger("SampLNS").basicConfig(
    format="%(levelname)s:%(message)s", level=logging.INFO
)
```

You can also pass a custom logger to the optimizer. This is useful if you want
to capture the log messages for analysis.

## Modules

### Parsing and Preprocessing

We parse the instances and preprocess them into instances where the essential
feature, i.e., features/variables that are not just auxiliary, are continously
indexed starting at zero. The other features are appended also as indices.
Additionally, some basic simplifications are performed, such as substituting
simple equality constraints or pulling unary clauses up.

This module should possibly be extracted and provide a simple export/import
functionallity.

### CDS

The CDS part tries to find tuples of feature literal-pairs that cannot appear
within the same sample. This is a very effective lower bound for the instances
we have seen and it also helps in the next step for symmetry breaking, which
speads up the individual LNS-steps fundamentally. For this purpose, it must not
only be able to compute CDS on the whole graph but also on a list of
pair-tuples.

### Sampling LNS

This is the heart of the optimizer and is surprisingly simple. Starting from a
given, feasible solution, it removes a few samples from the solution such that
at most a limited number of pairs get uncovered (the important observation here
is that only few pairs are covered by only one or very few samples, but they
involve the highest cost).

## Starting development

First, you should install all dependencies and run the package tests. You can do
so by simply executing the following commands at the root.

```shell
pip install -r requirements.txt
python3 setup.py install
python3 -m pytest -s tests
```

Now you can start developing. To check if something works early on, you may want
to write tests. Do so by simply adding a `test_something.py` directly besides
your source. The tests should be in functions called `def test_bla()` and use
`assert`. You can now test your code with

```shell
python3 setup.py develop
pytest -s pysrc
```

This will place the compiled binary in your source folder and run only the tests
within the source folder.

## Project Structure

Please follow the following project structure. It is carefully designed and
follows common guidelines. It uses
[Scikit-HEP developer information](https://scikit-hep.org/developer/intro) as
baseline.

- `cmake` Should contain all cmake utilities (no cmake package manager, so
  copy&paste)
- `deps` Should contain all dependencies
- `include` Public interfaces of C++-libraries you write. Should follow
  `include/libname/header.h`
- `python` Python packages you write. Should be of the shape
  `python/package_name/module_name/file.py`. Can be recursive.
- `notebooks` A place for Jupyter-notebooks.
- `src` Your implementation internals. Can also contain header files that are
  not part of the public interface!
- `tests` Your tests for C++ and Python. Read also
  [this](https://blog.ionelmc.ro/2014/05/25/python-packaging/#the-structure).
- `.clang_format` (C&P) C++-formatting rules, so we have a common standard.
  - Needs to be edited if: You want a different C++-coding style.
- `.flake8` (C&P) Python checking rules
  - Needs to be edited if: The rules do not fit your project. Especially, if
    there are too many false positives of some rule.
- `.gitignore` (C&P) Automatically ignore system specific files
  - Needs to be edited if: You use some uncommon tool that creates some kind of
    artifacts not covered by the current rules.
- `pyproject.toml` (C&P) Tells pip the dependencies for running `setup.py`.
  - Needs to be edited if: You use additional/different packages in `setup.py`
- `.pre-commit-config.yaml` (C&P) For applying a set of checks locally. Run,
  e.g., via `pre-commit run --all-files`.
  - Needs to be edited if: Better tools appear you would like to use, like a
    better `black` etc.
- `CMakeLists.txt` Defines your C++-project. This is a complex topic we won't
  dive into here. You should know the basics of CMake to continue.
- `conanfile.txt` Defines the C++-dependencies installed via conan (use CPM
  within CMakeLists.txt for copy&paste dependencies).
  - Needs to be edited if: You change C++-dependencies.
- `MANIFEST.in` (C&P) Defines all the files that need to be packaged for pip.
  - Needs to be edited if: You need some files included that do not fit the
    basic coding files, e.g., images.
- `setup.py` Scripts for building and installing the package.
  - Needs to be edited if: You add dependencies, rename the project, want to
    change metadata, change the project structure, etc.
  - If you don't have any CPP-components yet, you need to set the target to
    None!
- `requirements.txt` The recommended requirements for development on this
  package
  - Needs to be edited if: You are using further python packages.

## Common problems

Please report any further issues you encounter.

The package will build C++-code during installation using skbuild-conan.
If you encounter any problems during the installation, please check the
[skbuild-conan documentation](https://github.com/d-krupke/skbuild-conan#common-problems).