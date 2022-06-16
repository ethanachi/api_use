from collections import namedtuple
from dataclasses import dataclass
import json
import random
import time
from typing import Any, Callable, Dict, List, Optional

Function = namedtuple("Function", ("name", "definition", "args", "return_type", "library_name"))

class APITask:
  registry : Dict[str, Any] = dict()

  def __init__(self,
               id : str,
               library_name : str,
               functions: List[List[str]],
               style : str = "class"):
    """
    library_name: str (e.g. solids)
    functions: Dict[str, str]
    """
    self.id = id
    self.library_name = library_name
    self.functions = [Function(*[tuple(x) if isinstance(x, list) else x for x in l] + [self.library_name]) for l in functions]
    self.style = style
    assert self.style in ['class', 'import']
    self.num_distractors : int = -1
    self.do_import = False if style == 'class' else True

  @classmethod
  def add_to_registry(cls, id, *args, **kwargs):
    task = cls(id, *args, **kwargs)
    cls.registry[id] = task

  @classmethod
  def add_from_json(cls, data : Dict[str, Any]):
    functions = [[row['function_name'], row['documentation'], row['arglist'], row['return_type']] for row in data['functions']]
    task = cls(id=data['id'],
               library_name=data['library_name'],
               functions=functions,
               style=data['style'])

    cls.registry[data['id']] = task

  @classmethod
  def get_task(cls, id):
    return cls.registry[id]

  def generate_priming(self, target_func_name : str):
    """Returns the data for a target function, as well as all other feasible distractor functions."""

    target_func_defs = [func for func in self.functions if func.name == target_func_name]
    assert len(target_func_defs) > 0, f"No matching functions found for {target_func_name}; options include {[f.name for f in self.functions]}"
    assert len(target_func_defs) <= 1, f"Too many matching functions found for {target_func_name}"
    target_func_def = target_func_defs[0]

    funcs = [func for func in self.functions if func.name != target_func_name]
    return funcs, target_func_def
