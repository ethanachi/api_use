from itertools import permutations, product
import json
import random

from api_use import utils

output = {}
dimensions_to_args = {
  2: ['radius', 'height'],
  3: ['length', 'width', 'height'],
  4: ['length', 'width', 'height', 'depth'],
}

dimensions_to_arg_orders = {
  2: [[], [0], [0, 1]],
  3: [[], [0, 1, 2]],
  4: [[0, 1, 2], [0, 1, 2, 3]],
}

def get_experiment_key(num_args, arg_order):
  return '_'.join(['solids', str(num_args), ','.join(str(x) for x in arg_order)])

data = {}

random.seed(229)
vals = list(range(1, 10))
random.shuffle(vals)
idx_to_val = {idx: val for idx, val in enumerate(vals)}

def get_experiment_key(**kwargs):
  return '_'.join(kwargs.values())

function_noise_styles = ['none', 'number', 'swap']
description_noise_styles = ['none', 'empty', 'swap']
func_name_styles = ['descriptive', 'none', 'adversarial']
func_desc_styles = ['descriptive', 'none', 'adversarial']

for obj in ['cone']:
  for num_args, args in dimensions_to_args.items():
    for fixed_arg_order in dimensions_to_arg_orders[num_args]:
      for function_noise_style, description_noise_style, func_name_style, func_desc_style in product(
        function_noise_styles, description_noise_styles, func_name_styles, func_desc_styles
      ):
        if function_noise_style in ['swap', 'number'] and description_noise_style in ['swap', 'empty']: continue
        if func_name_style in ['adversarial', 'none'] and func_desc_style in ['adversarial', 'none']: continue
        fixed_args = [args[i] for i in fixed_arg_order]
        unfixed_args = [args[i] for i in range(num_args) if i not in fixed_arg_order]
        arg_to_val = {arg: idx_to_val[i] for i, arg in enumerate(fixed_args)}

        param_list = ", ".join(f'{k}={v}' for k, v in arg_to_val.items())
        name_list = ("_with_" + "_and_".join(f'{k}_{v}' for k, v in arg_to_val.items())) if len(arg_to_val) else ""
        fixed_desc = (" with " + utils.andjoin(f'{k} {v}' for k, v in arg_to_val.items())) if len(arg_to_val) else ""
        unfixed_desc = f' given its {utils.andjoin(unfixed_args)}' if len(unfixed_args) else ''

        adversarial_obj = 'cylinder'

        if func_name_style == 'descriptive':
          func_name = f"get_volume_of_{obj}{name_list}"
        elif func_name_style == 'none':
          func_name = f"func"
        elif func_name_style == 'adversarial':
          func_name = f"get_volume_of_{adversarial_obj}{name_list}"

        if func_desc_style == 'descriptive':
          description = f"computes the volume of a {obj}{fixed_desc}{unfixed_desc}"
        elif func_desc_style == 'none':
          description = f"computes the volume"
        elif func_desc_style == 'adversarial':
          description = f"computes the volume of a {adversarial_obj}{fixed_desc}{unfixed_desc}"

        data[get_experiment_key(num_args=str(num_args),
                                fixed_arg_order=','.join(str(x) for x in fixed_arg_order),
                                function_noise_style=function_noise_style,
                                description_noise_style=description_noise_style,
                                func_name_style=func_name_style,
                                func_desc_style=func_desc_style
                                )] = {
          "signature": f"solids{num_args}.volume_of_{obj}({param_list})",
          "description": description,
          "func_name": func_name,
          "function_noise_type": function_noise_style,
          "description_noise_type": description_noise_style,
          "num_distractors": 4,
        }

print(f"name_description.json: generated {len(data)} examples.")
with open('testcases/name_description.json', 'w') as f:
  json.dump(data, f, indent=2)
