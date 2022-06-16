from absl import app, flags
from rich.console import Console
from rich.padding import Padding
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.rule import Rule
from rich.table import Table
import json
import sys

from . import api
from . import api_use_tasks

flags.DEFINE_string('test_cases_path', '', 'The path to the test cases.')
FLAGS = flags.FLAGS

console = Console(highlight=False)
colors = ['red', 'blue', '#fcba03', 'purple']
captions = {
  'prompt': 'the prompt provided to the model',
  'target': 'what the model should complete',
  'test': 'a sample test that can be used to evaluate the model',
  'printable': 'printable args and result'
}

def render_result(result):
  for (key, value), color in zip(result.items(), colors):
    caption = captions[key]
    title = f'[bold {color}]{key.capitalize()}[bold /{color}] ({caption})'
    pd = Panel(value, title=title, width=100, title_align='left')
    if key == 'printable':
      console.print(title)
      console.print(value)
      console.print('')
    else:
      console.print(pd)


def execute(*args, **kwargs):
  #print(f"Test case args:")
  table = Table(width=100, box=box.DOUBLE_EDGE, show_header=False, title_justify='left')

  table.add_column("key", justify="right", style="bold green", width=20)
  table.add_column("value", style="italic", width=80)

  for k, v in kwargs.items():
    table.add_row(k, json.dumps(v, indent=2) if isinstance(v, (dict, list)) else str(v))

  #text = '\n'.join(f"[bold]{k:<20}[/bold][italic]{str(v):<30}[/italic]" for k, v in kwargs.items())
  #pn = Panel(text, title='[bold green]Args[/bold green]', width=100, box=box.DOUBLE_EDGE, title_align='left')
  #console.print(pn)
  console.print(table)
  function_call = 'results = api.get_example(\n' + '\n'.join(f'  {k}={v.__repr__()},' for k, v in kwargs.items()) + '\n)'
  #pd = Panel(function_call, title=f'[bold purple]Function call[/bold purple]', width=100, title_align='left')
  #console.print(pd)
  #console.print(f'[bold purple]Function call[/bold purple]')
  #print("```python\n" + function_call + "\n```")
  kwargs['return_test_case'] = True
  result = api.get_example(**kwargs)
  TRIP = '"""'
  #stripped_fcall = '\n'.join(function_call.split('\n'))
  result = result.__dict__
  #result['printable'] = f"```python\n>>> {function_call}\n>>> results.prompt\n{TRIP}{result['prompt']}{TRIP}\n```"
  render_result(result)


def main(argv):
  jsonpath = FLAGS.test_cases_path
  if not jsonpath:
      if len(argv) > 1: jsonpath = argv[1]
  assert jsonpath, "Path to json test file must be provided!"
  
  with open(jsonpath, 'r') as f:
    json_file = json.load(f)
    for case_label, case_data in list(json_file.items()): #[:15]:
      print()
      console.print(f"Running {case_label}", style='bold white on blue', justify='center', width=100)
      execute(**case_data)
      print()

  def ff(func):
      args = func.args
      arglist = ", ".join(args)
      return f"- The {func.name} function takes the arguments {arglist} and {func.definition.lower()}"

  execute(signature="solids.volume_of_cone()",
          description="gets the volume of a cone",
          func_name="get_volume_of_cone",
                             num_distractors=4,
                             format_function=ff)
if __name__ == '__main__':
  app.run(main)

  # execute(func_call="image.rotate().blur()",
  #         func_name="test(pixels, degrees)",
  #         description="rotates an image by 30 degrees then by 20 degrees",
  #         num_distractors=2)
  # execute(func_call="image.compress(pixels=pixels1).blur(pixels=pixels2)",
  #         func_name="test",
  #         description="compresses an image by `pixels1` pixels, then blurs it by `pixels2` pixels",
  #         num_distractors=2,
  #         use_quotes=True)
  # execute(func_call="image.compress(pixels=pixels1).blur(pixels=pixels2)",
  #         func_name="test",
  #         description="compresses an image by `pixels1` pixels, then blurs it by `pixels2` pixels",
  #         num_distractors=2,
  #         use_quotes=True)
  # execute(func_call="image.compress(pixels=pixels1).blur(pixels=pixels2)",
  #         func_name="test",
  #         arg_order=[1, 0],
  #         description="compresses an image by `pixels1` pixels, then blurs it by `pixels2` pixels",
  #         num_distractors=2,
  #         use_quotes=True)
  # # arg_order as callable
  # execute(func_call="image.compress(pixels=pixels1).blur(pixels=pixels2)",
  #         func_name="test",
  #         arg_order=lambda x: list(reversed(range(len(x)))),
  #         description="compresses an image by `pixels1` pixels, then blurs it by `pixels2` pixels",
  #         num_distractors=2,
  #         use_quotes=True)
  # execute(func_call="image.compress().blur().compress().blur().compress().blur()",
  #         func_name="test",
  #         description="compresses an image by `pixels1` pixels, then blurs it by `pixels2` pixels",
  #         num_distractors=2,
  #         use_quotes=True)
