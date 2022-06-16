from itertools import permutations
import json

# distractors_and_positioning.json

output = {}

for target_library in ['solids']:
  for target_function in ['volume_of_cone']:
    for num_distractors in range(8):
      for idx in range(num_distractors + 1):
        label = f'{target_library}-{target_function}-{num_distractors}-{idx}'
        output[label] = {
          "signature": f"{target_library}.{target_function}()",
          "description": f"gets the volume of a cone with the given radius and height",
          "func_name": "get_volume_of_cone",
          "num_distractors": num_distractors,
          "target_func_location": idx,
        }

print(f"distractors_and_positioning.json: generated {len(output)} examples.")
with open('testcases/distractors_and_positioning.json', 'w') as f:
  json.dump(output, f, indent=2)
