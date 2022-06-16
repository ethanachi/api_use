import json
from typing import List

from . import execution_utils

DUMMY_CODE = """
class Dummy:
  def __init__(self, s='main'):
    self.s = s
    self.func_calls = []
  def __eq__(self, other):
    return self.s == other.s
  def __getattr__(self, name):
    def func(*args, **kwargs):
      print(self.func_calls)
      signature = Dummy(self.s + "." + name + "(" +  ",".join(str(x) for x in args) + ")")
      #self.func_calls.append(signature)
      return signature
    return func
  def __str__(self):
    return 'D<' + self.s + '>'
  def __repr__(self):
    return str(self)
"""

def execute(sample, test):
  signature, indent, dummy_defn, style = test.split('\n')[:4]
  dummy_obj = dummy_defn.split(' ')[0]
  style = style.split('=')[1].strip()
  is_import_style = (style == "'import_style'")
  indent = indent.split("'")[1]
  prefix = signature.split('=')[1].strip() + '\n' + indent + f'global Dummy\n' + (f'{indent}global {dummy_obj}\n' if is_import_style else '') + indent
  test_setup = DUMMY_CODE + '\n' + dummy_defn
  #print("setup", test_setup)
  test = '\n'.join(test.split('\n')[3:])


  if not isinstance(sample, list): sample = [sample]
  # s = sample[0]
  # print(":::" + test_setup + '\n' + prefix + s)
  results = [
      execution_utils.run_tests(test_setup + '\n' + prefix + s, [test], test_setup_code="")
      for s in sample # tqdm.tqdm(sample)
  ]
  #print(json.dumps([r.error_text.split('\n') for r in results if r.error_text], indent=2))
  results = [(r.correct, r.error_text.replace('AssertionError: ', '') if r.error_text else None) for r in results]
  if len(results) == 1: results = results[0]
  return results

test = """# signature = def test(radius, height):
# indent = '    '
solids = Dummy()
x = test(radius="dummy_radius_0", height="dummy_height_1")
y = solids.volume_of_cone("dummy_radius_0", "dummy_height_1")
assert x == y, f'Test failure: {x} != {y}'"""

if __name__ == '__main__':
  result = execute("solids.volume_of_cone(radius, height)", test)
  print(result)
