# SampLNS

## Installation

This package requires a valid license of the commercial MIP-solver Gurobi.
You can get a free license for academic purposes.
These academic licenses are fairly easy to obtain, as explained
in [this video](https://www.youtube.com/watch?v=oW6ma8rdZk8):

- Register an academic account.
- Install Gurobi (very easy with Conda, you only need the tool `grbgetkey`).
- Use `grbgetkey` to set up a license on your computer.

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

## Often occurring problems

## GLIBCXX not found

If you get an error such as `E   ImportError: /home/krupke/anaconda3/envs/mo310/bin/../lib/libstdc++.so.6: version `GLIBCXX_3.4.30' not found (required by /home/krupke/anaconda3/envs/mo310/lib/python3.10/site-packages/samplns/cds/_cds_bindings.cpython-310-x86_64-linux-gnu.so)`, you are probably using conda (good!) but need to update glibcxx. Install the latest version by `conda install -c conda-forge libstdcxx-ng`.

## Changelog

- 0.4.0: Timeout for model building for UB. There seem to be some cases in which this
  takes forever.
