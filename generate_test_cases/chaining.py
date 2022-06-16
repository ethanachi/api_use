from itertools import permutations
import json
import random
#import utils

output = {}

RANDOM_SEEDS = list(range(20))

func_pool = [
  ("rotate()", "rotate", "rotates $ by the given number of degrees"),
  ("rotate(degrees=30)", "rotate_30_degrees", "rotates $ 30 degrees"),
  ("rotate(degrees=60)", "rotate_60_degrees", "rotates $ 60 degrees"),
  ("flip_horizontal()", "flip_horizontal", "flips $ horizontally"),
  ("flip_vertical()", "flip_vertical", "flips $ vertically"),
  ("blur()", "blur", "blurs $ by the given number of pixels"),
  ("blur(pixels=10)", "blur_10_px", "blurs $ by 10 pixels"),
  ("distort(pixels=image.get_width())", "distort", "distorts $ by the width of the image"),
  ("distort(pixels=5)", "distort_5_px", "distorts $ by 5 pixels"),
]

random.shuffle(func_pool)
num_functions = [1, 2, 3, 4, 5, 6, 7, 8]

random_seed_to_func_list = {}
for random_seed in RANDOM_SEEDS:
  random.seed(random_seed)
  functions_used = random.sample(func_pool, k=max(num_functions))
  #print(functions_used)
  random_seed_to_func_list[random_seed] = functions_used

for random_seed in RANDOM_SEEDS:
  for num_funcs in num_functions:
    #print(random_seed_to_func_list[random_seed][:num_funcs])
    #print(random_seed_to_func_list[random_seed])
    function_call_list, func_name_list, desc_list = zip(*random_seed_to_func_list[random_seed][:num_funcs])
    function_call = "image." + '.'.join(function_call_list)
    func_name = "_then_".join(func_name_list)
    desc = ", then ".join([desc_list[0].replace('$', 'an image')] + [x.replace('$', 'it') for x in desc_list[1:]])
    print(function_call, func_name, desc)

    # output[f'{num_funcs}_{random_seed}_{",".join(function_call_list)}'] = {
    #   "signature": function_call,
    #   "func_name": func_name,
    #   "description": desc,
    #   "num_distractors": max(3-num_funcs, 0),
    # }

    output[f'{num_funcs}_{random_seed}_{",".join(function_call_list)}_fewshot'] = {
      "signature": function_call,
      "func_name": func_name,
      "description": desc,
      "fewshot": [
        {
          "signature": "image.compress()",
          "func_name": "compress",
          "description": "compresses an image by the given number of pixels",
        }
      ],
      "num_distractors": max(3-num_funcs, 0),
    }


print(f"chaining.json: generated {len(output)} examples.")
with open('testcases/chaining.json', 'w') as f:
  json.dump(output, f, indent=2)
