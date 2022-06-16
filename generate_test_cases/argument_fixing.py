from itertools import permutations
import json
from api_use import utils

output = {}
dimensions_to_args = {
  2: ['radius', 'height'],
  3: ['length', 'width', 'height'],
  4: ['length', 'width', 'height', 'depth'],
}

def get_experiment_key(num_args, arg_order):
  return '_'.join(['solids', str(num_args), ','.join(str(x) for x in arg_order)])

data = {}

for num_args, args in dimensions_to_args.items():
  all_idxs = list(range(num_args))
  for num_unfixed in range(1, num_args+1):
    for fixed_arg_order in permutations(all_idxs, r=num_unfixed):
      fixed_args = [args[i] for i in fixed_arg_order]
      unfixed_args = [args[i] for i in all_idxs if i not in fixed_arg_order]

      param_list = ", ".join(f'{arg}={{val{i+1}}}' for i, arg in enumerate(fixed_args))
      name_list = "_and_".join(f'{arg}_{{val{i+1}}}' for i, arg in enumerate(fixed_args))
      desc_list = utils.andjoin([f'{arg} {{val{i+1}}}' for i, arg in enumerate(fixed_args)])

      desc = f' given its {utils.andjoin(unfixed_args)}' if len(unfixed_args) else ''

      data[get_experiment_key(num_args, fixed_arg_order)] = {
        "signature": f"solids{num_args}.volume_of_{{obj}}({param_list})",
        "description": f"computes the volume of a {{obj}} with {desc_list}{desc}",
        "func_name": f"get_volume_of_{{obj}}_with_{name_list}",
      }


targets = {"obj": "cone", "val1": 5, "val2": 4, "val3": 3, "val4": 2}
fewshot_targets = [
  {"obj": "cylinder", "val1": 2, "val2": 3, "val3": 8, "val4": 6},
  {"obj": "prism", "val1": 7, "val2": 2, "val3": 9, "val4": 3}
]

experiments = {}

def format_test_case(templates, parameterization):
  return {k: (v.format(**parameterization) if isinstance(v, str) else v) for k, v in templates.items()}

def add_fewshot_data(data, fewshot_examples):
  return {**data, **{'fewshot': fewshot_examples}}

def get_ood_key(experiment_name):
  _, num_args, fixed_arg_order = experiment_name.split('_')
  fixed_arg_order = [int(x) for x in fixed_arg_order.split(',')]
  if len(fixed_arg_order) == 1:
    return get_experiment_key(num_args, [(fixed_arg_order[0] + 1) % int(num_args)])
  return get_experiment_key(num_args, fixed_arg_order[::-1])

for key, iid_template in data.items():
  ood_template = data[get_ood_key(key)]
  iid_test_case = format_test_case(iid_template, targets)
  iid_test_case['num_distractors'] = 4

  output[key + '_0shot'] = iid_test_case
  iid_fewshot_examples = [format_test_case(iid_template, f) for f in fewshot_targets]
  ood_fewshot_examples = [format_test_case(ood_template, f) for f in fewshot_targets]

  for num_fewshot_examples in range(1, len(iid_fewshot_examples)+1):
    output[key + f'_{num_fewshot_examples}shot_iid'] = add_fewshot_data(iid_test_case,
      iid_fewshot_examples[:num_fewshot_examples]
    )
    output[key + f'_{num_fewshot_examples}shot_ood'] = add_fewshot_data(iid_test_case,
      ood_fewshot_examples[:num_fewshot_examples]
    )

  output[key + f'_2shot_iid_ood'] = add_fewshot_data(iid_test_case,
    [iid_fewshot_examples[0], ood_fewshot_examples[1]]
  )
  output[key + f'_2shot_ood_iid'] = add_fewshot_data(iid_test_case,
    [iid_fewshot_examples[1], ood_fewshot_examples[0]]
  )

print(f"argument_fixing.json: generated {len(output)} examples.")
with open('testcases/argument_fixing.json', 'w') as f:
  json.dump(output, f, indent=2)
