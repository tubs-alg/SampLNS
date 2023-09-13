"""
This package provides a preprocessor for instances.
```
from preprocessor import Preprocessor
index_instance = Preprocessor().preprocess(instance)
```
"""
# flake8: noqa F401
from .index_instance import IndexInstance
from .preprocessing import Preprocessor

__all__ = ["Preprocessor", "IndexInstance"]
