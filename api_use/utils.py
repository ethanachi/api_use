from collections import Counter, defaultdict
import random
import re
from typing import Any, Callable, Dict, List, Optional, Set, Union
from typing_extensions import Literal

from . import task

FUNCTION_NOISE_TYPES = Literal['swap', 'semantic_shuffle', 'number', 'none']
ARG_NOISE_TYPES = Literal['number', 'none']
DESC_NOISE_TYPES = Literal['swap', 'none', 'empty']

def derange(some_list):
  if len(some_list) == 1: return some_list
  randomized_list = some_list[:]
  while True:
    random.shuffle(randomized_list)
    for a, b in zip(some_list, randomized_list):
      if a == b:
        break
      else:
        return randomized_list

### ids for dummy tasks
used : List[int] = []
def get_nonrepeating_id() -> int:
  x = len(used)
  used.append(x)
  return x

def reset_nonrepeating_ids():
  used.clear()

def get_dummy_value(arg_id) -> str:
  return f'"dummy_{arg_id}_{get_nonrepeating_id()}"'

### utils for working with dictionaries
def intersect_if_exists(overall_dict : Dict[str, set],
                        key : str,
                        new_value : set):
  if key in overall_dict:
    overall_dict[key] = overall_dict[key].intersection(new_value)
  else:
    overall_dict[key] = set(new_value)

### function formatting utilities
def default_format_function(func : task.Function,
                            indent : str,
                            use_quotes : bool,
                            no_description : bool = False) -> str:
    args = func.args # self.get_distractor_args(len(func.args)) if FLAGS.modify_arguments else func.args
    arglist = ", ".join(args)
    quotable = '"""' if use_quotes else ''
    return f"def {func.library_name}.{func.name}({arglist})" + (f":\n{indent}{quotable}{func.definition}{quotable}" if not no_description else "")

def format_functions(funcs : List[task.Function],
                     format_function : Callable[[task.Function], str],
                     joiner : str ='\n'):
  out = joiner.join(format_function(func) for func in funcs)
  return out

def deduplicate_unfixed_params(unfixed_params : Dict[str, str]):
  unfixed_params_count = Counter(unfixed_params.values())
  used_so_far : defaultdict[str, int] = defaultdict(int)
  unfixed_param_mapping = dict(unfixed_params.items())
  for dummy_arg, unfixed_param in unfixed_param_mapping.items():
    if unfixed_params_count[unfixed_param] > 1:
      used_so_far[unfixed_param] += 1
      unfixed_params[dummy_arg] = unfixed_param + str(used_so_far[unfixed_param])


def extract_unspecified_arglist_from_func_name(func_name : str):
  if '(' in func_name:
    all_unspecified_arglist = func_name[func_name.index('(') + 1:func_name.index(')')]
    func_name = func_name[:func_name.index('(')]
  else:
    all_unspecified_arglist = ""
    func_name = func_name
  return func_name, all_unspecified_arglist


def process_definition(defn : str, old_arg_to_new_arg : Optional[Dict[str, str]]):
  pattern = r'\[([^\]]*)\|([^\]]*)\]'
  if old_arg_to_new_arg is None:
    return re.sub(pattern, r'the given \1', defn)
  else:
    def repl(matchobj):
      return 'the ' + matchobj.group(1) + ' ' + old_arg_to_new_arg[matchobj.group(2)]
    return re.sub(pattern, repl, defn)



def get_fname_mapping(function_pool : List[task.Function],
                      function_noise_type : Optional[FUNCTION_NOISE_TYPES] = None,
                      arg_noise_type : Optional[ARG_NOISE_TYPES] = None,
                      description_noise_type : Optional[DESC_NOISE_TYPES] = None):
  function_names = [f.name for f in function_pool]
  new_function_names = function_names.copy()

  if function_noise_type == 'swap':
    new_function_names = derange(new_function_names)
  elif function_noise_type == 'semantic_shuffle':
    assert False
  elif function_noise_type == 'number':
    new_function_names = [f"func{i}" for i in range(len(function_names))]

  arglists = [f.args for f in function_pool]
  new_arglists = [f.args for f in function_pool]
  new_definitions = [f.definition for f in function_pool]
  old_arg_to_new_args : List[Optional[Dict[str, str]]] = []
  if arg_noise_type == 'number':
    new_arglists = [[f"arg{i}" for i in range(len(arglist))] for arglist in new_arglists]
    old_arg_to_new_args = [{o_a: n_a for o_a, n_a in zip(old_arglist, new_arglist)} for old_arglist, new_arglist in zip(arglists, new_arglists)]
  else:
    old_arg_to_new_args = [None] * len(arglists)

  new_definitions = [process_definition(defn, old_arg_to_new_arg) for defn, old_arg_to_new_arg in zip(new_definitions, old_arg_to_new_args)]
  if description_noise_type == 'swap':
    new_definitions = derange(new_definitions)

  new_function_list = [task.Function(nf, nd, na, f.return_type, f.library_name)
                       for nf, nd, na, f in zip(new_function_names,
                                                new_definitions,
                                                new_arglists,
                                                function_pool)]
  of_to_nf = {f: nf for f, nf in zip(function_names, new_function_names)}
  return of_to_nf, new_function_list

def replace_keys(target : str, d : Dict[str, str]):
  for k, v in d.items():
    target = target.replace(k, v)
  return target

def intersperse(insert_list : List[Any], base_list : List[Any]):
  if len(base_list) == 0: return insert_list
  n_blocks = len(insert_list) + 1
  block_length = max(len(base_list) // n_blocks, 1)
  out = []
  for i in range(n_blocks-1):
    out += base_list[i*block_length:(i+1)*block_length]
    out.append(insert_list[i])
  out += base_list[(n_blocks-1)*block_length:]
  return out

## Formatting utilities

def spacify(attr):
  return attr.replace('_', ' ')

def an(item):
  VOWELS = 'aeiou'
  return ('an ' if any(item.startswith(v) for v in VOWELS) else 'a ') + item

def andjoin(arr):
  arr = list(arr)
  if len(arr) == 0: return ""
  if len(arr) == 1: return arr[0]
  return ', '.join(arr[:-1]) + ' and ' + arr[-1]
