import ast
from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import partial
import random
import sys
from typing import Any, Callable, Dict, List, Optional, Set, Union
from typing_extensions import Literal

from . import task
from . import utils

@dataclass
class TaskIdCallData:
  distractor_funcs : Optional[Set[task.Function]] = None
  target_funcs : Optional[Set[task.Function]] = None
  count : int = 0

  def intersect_distractor_funcs(self, new_distractor_funcs : Set[task.Function]):
    if self.distractor_funcs is not None:
      self.distractor_funcs = self.distractor_funcs.intersection(new_distractor_funcs)
    else:
      self.distractor_funcs = new_distractor_funcs

  def add_target_func(self, target_func : task.Function):
    if self.target_funcs is None: self.target_funcs = set()
    self.target_funcs.add(target_func)

  def augment_targets(self, other_data : "TaskIdCallData"):
    if self.target_funcs is None: self.target_funcs = set()
    self.target_funcs |= other_data.target_funcs

  def __repr__(self):
    return f"{{dfuncs: {self.distractor_funcs}, tfuncs: {self.target_funcs}, count: {self.count} }}"

@dataclass
class TestCase:
  prompt : str
  target: str
  test: str

def create_preamble(task_id, unspecified_params):
  task_ = task.APITask.get_task(task_id)
  if task_.do_import:
    preamble = f"import {task_.library_name}\n"
    return preamble, unspecified_params, task_.library_name
  else:
    preamble = f"" #{task_.library_name} = {task_id.capitalize()}()\n"
    return preamble, [task_.library_name] + unspecified_params, task_.library_name

def handle_data(data : ast.Call):
  unfixed_params: Dict[str, str] = {} # from dummy value to global parameter

  task_id_to_data : Dict[str, TaskIdCallData] = defaultdict(TaskIdCallData)
  global_target : str = ""

  def handle_node(node : ast.Call):
    nonlocal global_target
    assert isinstance(node, ast.Call)

    value = node.func.value # type: ignore
    if isinstance(value, ast.Name):
      parent_id = value.id
      task_ = task.APITask.get_task(parent_id)
      parent_target = task_.library_name
      global_target = parent_id
    else:
      parent_id, parent_target = handle_node(value)

    task_ = task.APITask.get_task(parent_id)
    task_id = task_.id


    func_name = node.func.attr # type: ignore

    def handle_arg(nd):
      if isinstance(nd, ast.Str):
        return True, '"' + nd.s + '"'
      elif isinstance(nd, ast.Num):
        return True, str(nd.n)
      elif isinstance(nd, ast.Call):
        id, target = handle_node(nd)
        return True, target
      elif isinstance(nd, ast.Name):
        return False, nd.id
      else:
        print(ast.dump(nd))
        assert False

    distractor_func_list, target_func = task_.generate_priming(func_name)
    task_id_to_data[task_id].count += 1
    task_id_to_data[task_id].intersect_distractor_funcs(set(distractor_func_list))
    task_id_to_data[task_id].add_target_func(target_func)

    all_args = target_func.args
    signature_kws = [kw.arg for kw in node.keywords]
    assert len(signature_kws) == len(set(node.keywords)), "Duplicate keywords in function call."
    assert len(set(signature_kws) - set(all_args)) == 0, f"""Parameter listed in function call
{[kw.arg for kw in node.keywords]} does not appear in the arguments for function
{target_func.name}, which are {all_args}!"""

    local_arglist = {}

    for arg in all_args:
      kw = next((kw for kw in node.keywords if kw.arg == arg), None)
      dummy_val = utils.get_dummy_value(arg)
      if kw:
        is_fixed, value = handle_arg(kw.value)
        if is_fixed:
          local_arglist[arg] = value
        else:
          unfixed_params[dummy_val] = value
          local_arglist[arg] = dummy_val
      else:
          unfixed_params[dummy_val] = arg
          local_arglist[arg] = dummy_val

    local_arglist_str = ', '.join(local_arglist.values())
    target = f"{parent_target}.{target_func.name}({local_arglist_str})"
    return target_func.return_type, target

  _, target = handle_node(data)

  utils.deduplicate_unfixed_params(unfixed_params)
  human_readable_target = target
  for dummy_val, arg_name in unfixed_params.items():
    human_readable_target = human_readable_target.replace(dummy_val, arg_name)
  #print('tikkk', task_id_to_data)
  return target, {
    'unfixed_params': unfixed_params,
    'task_id_to_data': task_id_to_data,
    'global_target': global_target,
    'human_readable_target': human_readable_target,
  }


def format_prompt(*,
                  signature : str,
                  description,
                  func_name : str = 'func',
                  arg_order : Optional[Union[List[int], Callable[[List[str]], List[int]]]] = None,
                  task_description_preamble : str,
                  begin_token : str,
                  indent : str,
                  end_token : str = '[END]',
                 ):

  func_name, outer_arglist = utils.extract_unspecified_arglist_from_func_name(func_name)
  target, attrs = handle_data(ast.parse(signature).body[0].value) # type: ignore

  outer_args = list(attrs['unfixed_params'].values())
  global_target = attrs['global_target']
  preamble, outer_args, global_target = create_preamble(global_target, outer_args)

  if arg_order:
    if callable(arg_order): arg_order = arg_order(outer_args)
    assert len(set(arg_order)) == len(arg_order), "Duplicate arg_order elements detected."
    assert len(arg_order) == len(outer_args), f"There are {len(arg_order)} elements in the arg_order, but {len(outer_args)} arguments in the global function: {outer_args}."
    assert max(arg_order) == len(arg_order) - 1, "Invalid number in arg_order"
    outer_args = [outer_args[i] for i in arg_order]

  # create the unspecified arglist
  assert not(outer_arglist and arg_order), f"""An arglist was specified
in both the signature ({outer_arglist}) and `arg_order` argument
({arg_order})."""

  if not outer_arglist:
    outer_arglist = ', '.join(outer_args)
  prefix = f"def {func_name}({outer_arglist}):"

  class_style = (preamble == "")
  dummy_argcall = ', '.join([f'{v}={k}' for k, v in attrs['unfixed_params'].items()] + ([f"{global_target}={global_target}"] if class_style else []))

  test_call = f"{func_name}({dummy_argcall})"
  #print('class_style' if class_style else 'import_style')
  test = f"# signature = {prefix}\n# indent = '{indent}'\n{global_target} = Dummy()\n# style = '{'class_style' if class_style else 'import_style'}'\nx = {test_call}\ny = $TARGET\nassert x == y, f'Test failure: {{x}} != {{y}}'"

  instructions = f"""{task_description_preamble}{description}.\n{begin_token}\n{preamble}{prefix}\n{indent}"""
  instructions_completed = f"""{instructions}return {attrs['human_readable_target']}\n{end_token}"""

  return {
    "task_id_to_data": attrs['task_id_to_data'],
    "instructions": instructions,
    "instructions_completed": instructions_completed,
    "target": target,
    "human_readable_target": attrs['human_readable_target'],
    "test": test,
    "label": f"{func_name}({outer_arglist})",
  }


def select_distractors(task_id_to_data : Dict[str, TaskIdCallData],
                                  num_distractors : Union[int, Dict[str, int]],
                                  target_func_location : Union[int, float, Dict[str, int], Dict[str, float]],
                                  ):
  if isinstance(num_distractors, int):
    total_library_calls = sum([data.count for data in task_id_to_data.values()])
    distractor_weighting = {task_id: num_distractors * data.count // total_library_calls for task_id, data in task_id_to_data.items()}
  elif isinstance(num_distractors, dict):
    distractor_weighting = num_distractors

  function_pool = []
  for task_id, k in distractor_weighting.items():
    assert k <= len(task_id_to_data[task_id].distractor_funcs), f"{k} distractors requested, but only {len(task_id_to_data[task_id].distractor_funcs)} available"
    distractor_pool_task_id = random.sample(sorted(task_id_to_data[task_id].distractor_funcs), k=k)
    target_funcs = list(task_id_to_data[task_id].target_funcs)
    # insert the true functions in each distractor pool
    # [TODO] work on this
    if isinstance(target_func_location, float):
        target_func_location = int(target_func_location * len(distractor_pool_task_id))
    if isinstance(target_func_location, int):
      if target_func_location == -1:
        func_pool_task_id = utils.intersperse(target_funcs, distractor_pool_task_id)
        function_pool += func_pool_task_id
      else:
        assert len(target_funcs) == 1, "Too many target funcs!"
        func_pool_task_id = distractor_pool_task_id.copy()
        func_pool_task_id.insert(target_func_location, target_funcs[0])
        function_pool += func_pool_task_id
      # else:
      #   func_pool_task_id =
    else:
      assert False

  return function_pool

def global_function_name_noising(function_pool, function_noise_type, arg_noise_type, desc_noise_type, target, human_readable_target):
  fname_to_renamed_fname, function_pool = utils.get_fname_mapping(function_pool, function_noise_type, arg_noise_type, desc_noise_type)
  target = utils.replace_keys(target, fname_to_renamed_fname)
  human_readable_target = utils.replace_keys(human_readable_target, fname_to_renamed_fname)
  return fname_to_renamed_fname, function_pool, target, human_readable_target

def get_data_for_func_call(
    signature : str,
    description : str,
    *,
    func_name : str = 'func',
    num_distractors : Union[int, Dict[str, int]] = 0,
    target_func_location : Union[int, float, Dict[str, int], Dict[str, float]] = -1,
    arg_order : Optional[Union[List[int], Callable[[List[str]], List[int]]]] = None,
    task_description_preamble : str = "Write a function that ",
    fewshot: List[Dict[Any, Any]] = [],
    fewshot_style: Literal['combine', 'repeat'] = 'combine',
    function_noise_type : utils.FUNCTION_NOISE_TYPES = 'none',
    arg_noise_type : Optional[utils.ARG_NOISE_TYPES] = 'none',
    description_noise_type : utils.DESC_NOISE_TYPES = 'none',
    indent : Union[str, int] = 4,
    use_quotes : bool = False,
    joiner : str = '\n',
    section_joiner : str = '\n\n',
    intro : str = "Consider the following functions:",
    format_function : Optional[Callable[[task.Function], str]] = None,
    begin_token : str = "[BEGIN]",
    random_seed : Any = 229,
  ):

  random.seed(random_seed)
  utils.reset_nonrepeating_ids()

  if isinstance(indent, int):
    indent = ' ' * indent

  # one list of distractors for each. use the main distractor list, but actual function calls count against # of distractors
  # so make sure to add a check for whether you've exceeded the # of distractors with your # of calls
  # or should it not count?

  # implementation: add the fewshot function calls to the list of distractors...

  # support two different fewshot styles: combine all-the-promptings or

  # providing default vals for fewshot
  default_vals = {
    'arg_order': arg_order,
    'task_description_preamble': task_description_preamble,
    'begin_token': begin_token,
    'indent': indent,
  }
  func_call_results = format_prompt(signature=signature,
                                    description=description,
                                    func_name=func_name,
                                    arg_order=arg_order,
                                    task_description_preamble=task_description_preamble,
                                    begin_token=begin_token,
                                    indent=indent)
  ## [TODO] Add a test where the default args bleed into fewshot args
  fewshot_results = [format_prompt(**{**default_vals, **data}) for data in fewshot]

  def generate_formatted_function_list(function_pool, target, human_readable_target):
    fname_to_renamed_fname, function_pool, target, human_readable_target = global_function_name_noising(function_pool, function_noise_type, arg_noise_type, description_noise_type, target, human_readable_target)

    ff = format_function or partial(utils.default_format_function, indent=indent, use_quotes=use_quotes, no_description=(description_noise_type=='empty'))
    formatted_function_list = intro + '\n\n' + utils.format_functions(function_pool, ff, joiner=joiner)

    return formatted_function_list, target, human_readable_target

  if fewshot_style == 'combine':
    fewshot_instructions_and_answers = section_joiner.join((fewshot_result['instructions_completed'] for fewshot_result in fewshot_results))
    if fewshot_instructions_and_answers: fewshot_instructions_and_answers += section_joiner
    for fewshot_result in fewshot_results:
      for task_id, data in fewshot_result['task_id_to_data'].items():
        func_call_results['task_id_to_data'][task_id].augment_targets(data)
      ## [TODO] Add a test where the distractor is from a different library
    function_pool = select_distractors(task_id_to_data=func_call_results['task_id_to_data'],
                                       num_distractors=num_distractors,
                                       target_func_location=target_func_location)
    formatted_function_list, target, human_readable_target = generate_formatted_function_list(function_pool, func_call_results['target'], func_call_results['human_readable_target'])
    prompt = formatted_function_list + section_joiner + fewshot_instructions_and_answers + func_call_results['instructions']

  # elif fewshot_style == 'repeat':
  # not yet implemented

  else:
    raise ValueError(f"Fewshot style {fewshot_style} not recognized.")


  return {
    "prompt": prompt,
    "formatted_function_list": formatted_function_list,
    "target": human_readable_target,
    "test": func_call_results['test'].replace('$TARGET', target),
  }

def get_example(*args, return_test_case : bool = True, **kwargs):
  results = get_data_for_func_call(*args, **kwargs)
  return TestCase(prompt=results['prompt'], target='return ' + results['target'], test=results['test'])
