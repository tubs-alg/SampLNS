"""
```
from preprocessor import Preprocessor

index_instance = Preprocessor().preprocess(instance)
```
"""
# flake8: noqa F401
from .preprocessing import Preprocessor
from .index_instance import IndexInstance

__all__ = ["Preprocessor", "IndexInstance"]