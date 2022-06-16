import concurrent.futures
from functools import partial
import json
import os
import random
import requests
import string
import time

from absl import app
from absl import flags

from api_use import api
from api_use import api_use_tasks
from api_use import execution
RULE = '-' * 80 + '\n'

flags.DEFINE_string('model_type', "codex", 'The model type.')
flags.DEFINE_string('rpn', "cushman", 'The name of the model.')
flags.DEFINE_string('test_cases_path', "", 'The path to the test cases')
flags.DEFINE_string('temperature', "0.5", 'The temperature')
flags.DEFINE_string('base_path', "." 'The base path')
flags.DEFINE_integer('num_decodes', 128, 'The number of decodes desired')
flags.DEFINE_integer('max_tokens', 128, 'The maximum number of tokens desired')
flags.DEFINE_string('openai_key', "", 'The openai key (for codex probing)')
FLAGS = flags.FLAGS

import sys

USE_GFILE = False
if USE_GFILE:
  from google3.pyglib import gfile
  open_ = gfile.Open
  mkdirs = gfile.MakeDirs
else:
  open_ = open
  mkdirs = partial(os.makedirs, exist_ok=True)

def make_request_openai(prompt,
                        model_type='davinci',
                        temperature=0.5):
  for i in range(3):
    response = requests.post(f'https://api.openai.com/v1/engines/code-{model_type}-001/completions', json={
      "prompt": prompt,
      "stop": "[END]",
      "max_tokens": FLAGS.max_tokens,
      "temperature": float(temperature),
      "n": FLAGS.num_decodes,
    }, headers={
      'Authorization': f'Bearer {FLAGS.openai_key}'
    })
    if 'is currently overloaded' in response.text or 'Rate limit' in response.text:
      time.sleep(60*i)
    else:
      break
  assert response.status_code == 200, response.text
  return [x['text'] for x in response.json()['choices']]

def generate_label():
    random.seed()
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

def sample_from_test_case(test_case, test_case_id, sample_fn):
  results = api.get_example(**test_case)
  return test_case_id, sample_fn(results.prompt), results

def clean_decodes(decodes, cutoff='[END]'):
  out = []
  for result in decodes:
    if cutoff in result:
      result = result[:result.index(cutoff)]
    result = result.split('\n\n')[0]
    out.append(result)
  return out

def execute_test_cases(test_cases, sample_fn, experiment_dir, summary_filename, do_threading=False):
  test_case_id_to_decodes = {}
  if do_threading:
    pass
    # with concurrent.futures.ThreadPoolExecutor() as executor:
    #   futures = []
    #   for test_case_id, test_case in test_cases.items():
    #     futures.append(executor.submit(sample_from_test_case,
    #                                    test_case=test_case,
    #                                    test_case_id=test_case_id,
    #                                    sample_fn=sample_fn))
    #     print(f"Submitted {test_case_id}")
    #     time.sleep(5) # avoid smashing openai endpoint
    #   for (test_case_id, samples, results) in concurrent.futures.as_completed(futures):
    #     test_case_id_to_decodes[test_case_id] = samples
  else:
    outputs = {}
    for test_case_id, test_case in test_cases.items():
      a = time.time()
      _, decodes, data = sample_from_test_case(test_case, test_case_id, sample_fn)
      latency = time.time() - a
      decodes = clean_decodes(decodes)

      execution_outputs = execution.execute(decodes, data.test)

      total = len(decodes)
      correct = sum(output[0] for output in execution_outputs)
      accuracy = correct / total
      summary = f'{test_case_id}\t{accuracy:.3f}\t{correct}/{total}\t{latency:.4f}s'
      with open(summary_filename, 'a') as fp:
        fp.write(f"{summary}\n")
      print(summary)

      decodes_file = os.path.join(experiment_dir, test_case_id + '.decodes')
      with open(decodes_file, 'w') as decodes_file:
        decodes_file.write(json.dumps(test_case, indent=2) + '\n')
        decodes_file.write("Prompt: " + data.prompt + '\n')
        for (decode, result) in zip(decodes, execution_outputs):
          decodes_file.write(RULE)
          decodes_file.write('Correct: ' + str(result[0]) + '\n')
          decodes_file.write('Error: ' + str(result[1]) + '\n')
          decodes_file.write(RULE)
          decodes_file.write(str(decode) + '\n')
          decodes_file.write(RULE)

      outputs[test_case_id] = (decodes, execution_outputs, data)
      if FLAGS.model_type == 'codex': time.sleep(5) # avoid smashing openai endpoint
    return outputs

def main(argv):
  model_type = FLAGS.model_type
  rpn = FLAGS.rpn

  test_cases_path = FLAGS.test_cases_path
  if not test_cases_path and len(argv) > 1:
      test_cases_path = argv[1]
  assert test_cases_path, "test cases path must not be empty!"
  base_path = os.path.expanduser(FLAGS.base_path)
  label = generate_label()
  experiment_dir = os.path.join(base_path, label) + '/'
  print("Experiment outputs:", experiment_dir)
  mkdirs(experiment_dir)

  if model_type == 'codex':
    sample_fn = lambda prompt: make_request_openai(prompt=prompt, temperature=FLAGS.temperature)
  else:
    assert False, "Model type not recognized"

  with open(test_cases_path, 'r') as f:
    data = json.load(f)

  summary_filename = os.path.join(experiment_dir, 'summary.txt')
  execute_test_cases(data, sample_fn, experiment_dir, summary_filename)

if __name__ == "__main__":
  app.run(main)
