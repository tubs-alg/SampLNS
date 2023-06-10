# SampLNS: A Large Neighborhood Search to compute near minimal samples for feature models


SampLNS is an LNS-based optimizer for pairwise configuration sampling that comes with a lower bound proving technique.
On many of the instances we tested, it is able to compute smaller samples than YASA and frequently to even prove optimality.
A paper describing the approach is currently in progress.

The implementation is for research purposes only and not yet ready for production.
Please contact us if you want to use it in production.

**What is a Large Neighborhood Search (LNS)?**
It is a metaheuristic for optimization problems that works as follows:
You start with a feasible solution.
Then, you iteratively destroy a part if the solution and try to repair it in a way that improves the solution.
We are using Mixed Integer Programming and a SAT-based approach to do so, which allows us to find optimal solutions for the repair step.
Mixed Integer Programming is a powerful technique that can solve many NP-hard problems optimally up to a reasonable size.
The size of the destroyed part is scaled automatically to be as large as possible while still being able to find a repair.
The larger the destroyed part, the more likely it is to escape local minima and find an even better solution, potentially even an optimal solution.

**What is a lower bound and why is it useful?**
A lower bound is a value that is guaranteed to be smaller than the optimal solution.
If you have a lower bound, you can stop the optimization process as soon as you reach it.
The lower bound proves that you cannot find a better solution.
If the optimization process is not able to match it, the lower bound at least gives you a
guaranteed upper bound on the error of your solution.
Computing perfect lower bounds for NP-hard problems is itself NP-hard, so we are only able to
approximate them.
However, every lower bound returned is still guaranteed to be smaller than the optimal solution.
It may just not be sufficient to prove optimality.

## Installation

This package requires a valid license of the commercial MIP-solver Gurobi.
You can get a free license for academic purposes.
These academic licenses are fairly easy to obtain, as explained
in [this video](https://www.youtube.com/watch?v=oW6ma8rdZk8):

- Register an academic account.
- Install Gurobi (very easy with Conda, you only need the tool `grbgetkey`).
- Use `grbgetkey` to set up a license on your computer. You may have to be within the
  university network for this to work.

After you got your license, move into the folder with `setup.py` and run

```shell
pip install .
```

This should automatically install dependencies and build the package for you.
Only tested with Linux. Potentially works with Mac OS, likely fails with Windows.

> If you got a bad license, the code may just crash without a proper error message. This
> will be fixed soon.

## Usage

There is an example in `examples/`.

```python
import json

from samplns.simple import ConvertingLns
from samplns.instances import parse
from samplns.lns import RandomNeighborhood

if __name__ == "__main__":
    feature_model = parse("./toybox_2006-10-31_23-30-06/model.xml")
    with open("./yasa_sample.json") as f:
        initial_sample = json.load(f)
    solver = ConvertingLns(
        instance=feature_model,
        initial_solution=initial_sample,
        neighborhood_selector=RandomNeighborhood(),
    )

    solver.optimize(
        iterations=10000,
        iteration_timelimit=60.0,
        timelimit=900,
    )
    optimized_sample = solver.get_best_solution(verify=True)
    print(
        f"Reduced initial sample of size {len(initial_sample)} to {len(optimized_sample)}")
    print(f"Proved lower bound is {solver.get_lower_bound()}.")
```

> ! The samples have to be lists of fully defined dictionaries. Otherwise, the results may
> be wrong. We will add automatic warnings for that soon.

> ! There is no CLI, yet. We will add it with the next version.

## Modules

### Parsing and Preprocessing

We parse the instances and preprocess them into instances where the
essential feature, i.e., features/variables that are not just auxiliary,
are continously indexed starting at zero. The other features are appended
also as indices. Additionally, some basic simplifications are performed,
such as substituting simple equality constraints or pulling unary clauses up.

This module should possibly be extracted and provide a simple export/import
functionallity.

### CDS

The CDS part tries to find tuples of feature literal-pairs that cannot appear
within the same sample. This is a very effective lower bound for the instances
we have seen and it also helps in the next step for symmetry breaking, which
speads up the individual LNS-steps fundamentally. For this purpose, it must
not only be able to compute CDS on the whole graph but also on a list of
pair-tuples.

### Sampling LNS

This is the heart of the optimizer and is surprisingly simple. Starting
from a given, feasible solution, it removes a few samples from the solution
such that at most a limited number of pairs get uncovered (the important
observation here is that only few pairs are covered by only one or very few
samples, but they involve the highest cost).

## Starting development

First, you should install all dependencies and run the package tests. You can do so by
simply executing the following commands at the root.

```shell
pip install -r requirements.txt
python3 setup.py install
python3 -m pytest -s tests
```

Now you can start developing. To check if something works early on, you may want to write
tests.
Do so by simply adding a `test_something.py` directly besides your source. The tests
should
be in functions called `def test_bla()` and use `assert`. You can now test your code with

```shell
python3 setup.py develop
pytest -s python
```

This will place the compiled binary in your source folder and run only the tests within
the
source folder.

## Project Structure

Please follow the following project structure. It is carefully designed and follows
common guidelines. It uses
[Scikit-HEP developer information](https://scikit-hep.org/developer/intro) as baseline.

- `cmake` Should contain all cmake utilities (no cmake package manager, so copy&paste)
- `include` Public interfaces of C++-libraries you write. Should
  follow `include/libname/header.h`
- `python` Python packages you write. Should be of the
  shape `python/package_name/module_name/file.py`. Can be recursive.
- `notebooks` A place for Jupyter-notebooks.
- `src` Your implementation internals. Can also contain header files that are not part of
  the public interface!
- `tests` Your tests for C++ and Python. Read
  also [this](https://blog.ionelmc.ro/2014/05/25/python-packaging/#the-structure).
- `.clang_format` (C&P) C++-formatting rules, so we have a common standard.
    - Needs to be edited if: You want a different C++-coding style.
- `.flake8` (C&P) Python checking rules
    - Needs to be edited if: The rules do not fit your project. Especially, if there are
      too many false positives of some rule.
- `.gitignore` (C&P) Automatically ignore system specific files
    - Needs to be edited if: You use some uncommon tool that creates some kind of
      artifacts not covered by the current rules.
- `pyproject.toml` (C&P) Tells pip the dependencies for running `setup.py`.
    - Needs to be edited if: You use additional/different packages in `setup.py`
- `.pre-commit-config.yaml` (C&P) For applying a set of checks locally. Run, e.g.,
  via `pre-commit run --all-files`.
    - Needs to be edited if: Better tools appear you would like to use, like a
      better `black` etc.
- `CMakeLists.txt` Defines your C++-project. This is a complex topic we won't dive into
  here. You should know the basics of CMake to continue.
- `conanfile.txt` Defines the C++-dependencies installed via conan (use CPM within
  CMakeLists.txt for copy&paste dependencies).
    - Needs to be edited if: You change C++-dependencies.
- `MANIFEST.in` (C&P) Defines all the files that need to be packaged for pip.
    - Needs to be edited if: You need some files included that do not fit the basic coding
      files, e.g., images.
- `setup.py` Scripts for building and installing the package.
    - Needs to be edited if: You add dependencies, rename the project, want to change
      metadata, change the project structure, etc.
    - If you don't have any CPP-components yet, you need to set the target to None!
- `requirements.txt` The recommended requirements for development on this package
    - Needs to be edited if: You are using further python packages.

## Common problems

Please report any further issues you encounter.

### `RuntimeError: Caught an unknown exception!`

Probably, you have a bad Gurobi-license. We currently do not have a good way of checking that.

### glibcxx problems: 

If you get an error such as 
```
ImportError: /home/krupke/anaconda3/envs/mo310/bin/../lib/libstdc++.so.6: version `GLIBCXX_3.4.30' not found (required by /home/krupke/anaconda3/envs/mo310/lib/python3.10/site-packages/samplns/cds/_cds_bindings.cpython-310-x86_64-linux-gnu.so)
```
you are probably using conda (good!) but need to update glibcxx. Install the latest version by 
```sh
conda install -c conda-forge libstdcxx-ng
```

### ABI problems: Undefined symbol `...__cxx1112basic_stringIcSt11char_...`

This problem should be automatically fixed. Please open an issue if you still encounter it.

See [https://docs.conan.io/1/howtos/manage_gcc_abi.html](https://docs.conan.io/1/howtos/manage_gcc_abi.html) for more details.

## Changelog

- 0.7.0: Adding zip support for instances.
- 0.6.0: Newly packed version for GitHub. More stable build and stuff.
- 0.4.0: Timeout for model building for UB. There seem to be some cases in which this
  takes forever.
