"""Utilities for evaluating and formatting examples."""

import ast
import collections
import contextlib
import copy
import dataclasses
import enum
import io
import itertools
import json
import multiprocessing as mp
import signal
import sys
import traceback
import types
from typing import Any, Dict, List, Optional

from absl import logging
import astunparse

@contextlib.contextmanager
def suppress_stdio():
  """Prevents anything in the enclosing context from printing."""
  stdout = sys.stdout
  stderr = sys.stderr
  sys.stdout = None
  sys.stderr = None

  try:
    yield
  finally:
    sys.stdout = stdout
    sys.stderr = stderr

@contextlib.contextmanager
def register_alarm(signal_id, handler):
  """Registers an alarm for a particular signal, and resets it afterwards."""
  old_handler = signal.signal(signal_id, handler)
  try:
    yield
  finally:
    signal.signal(signal_id, old_handler)

def exec_with_timeout(code: str, timeout: int = 10) -> Dict[str, str]:
  """A safe version of exec which allows for a timeout exception.

  Args:
    code: the code text to execute.
    timeout: a timeout value in seconds to execute
  Returns:
    dictionary with variables from local execution.

  Raises:
    ValueError: on any exception in the subprocess.
    TimeoutError: on any timeout.
  """

  def alarm_handler(signum, frame):
    raise TimeoutError

  with register_alarm(signal.SIGALRM, alarm_handler):
    signal.alarm(timeout)

    try:
      with suppress_stdio():
        var_dict = {}
        exec(code, {}, var_dict)  # pylint: disable=exec-used
        return var_dict
    except TimeoutError:
      raise TimeoutError(f'The function was not able to complete before '
                         f'the timeout ({timeout} sec) occurred.')
    except (Exception, SystemExit):
      trace = traceback.format_exc()
      raise ValueError(f'An exception occurred while calling exec. '
                       f'Traceback:\n\n{trace}')
    finally:
      signal.alarm(0)


class ResultType(enum.Enum):
  SUCCESS = 1  # The code executed without crashing and returned results.
  RUNTIME_ERROR = 2   # The code failed at runtime.
  NO_REPLY_ERROR = 3  # The code did not reply due to timeout
  SYNTAX_ERROR = 4  #  The code did not even compile due to a syntax error
  REPLY_WAS_NONE = 5  # A catchall error - I'm not 100% sure I understand all of
  # the reasons this can happen, but it at least happens when imports fail.
  MEMORY_ERROR = 5  # Memory error which might occur despite of sandboxing.

@dataclasses.dataclass
class TestResult:
  code: str
  test_list: List[str]
  correct: bool
  error_text: Optional[str]
  traceback: Optional[str]

def test_string_from_list(test_list: List[str]):
  """Converts a list of tests into a string for prompts."""
  test_string = ''
  for idx, test in enumerate(test_list):
    test_string += test
    if idx != len(test_list) - 1:
      test_string += '\n'
  return test_string

def run_tests(code: str,
                        test_list: List[str],
                        test_setup_code: str = '',
                        timeout: int = 10) -> TestResult:
  """Evaluates a code snipppet on a set of tests.

  Args:
    code: the code itself as a string.
    test_list: the set of test cases to evaluate. These should be executable
      given the code provided.
    test_setup_code: code we must run to set up the tests.
    timeout: a timeout value at which point the code automatically fails.

  Returns:
    a TestResult object containing details about the evaluation.
  """
  test_code = code + '\n\n' + test_setup_code + '\n'
  test_code += test_string_from_list(test_list)

  logging.debug('EXECUTING TESTS:')
  logging.debug('=' * 80)
  logging.debug(test_code)
  logging.debug('=' * 80)

  try:
    exec_with_timeout(test_code, timeout=timeout)
    return TestResult(
        code=code,
        test_list=test_list,
        correct=True,
        error_text=None,
        traceback=None,
    )
  except (ValueError, TimeoutError) as e:
    logging.debug('=' * 80)
    logging.debug('Test completed with error:')
    logging.debug(e)
    logging.debug('=' * 80)

    return TestResult(
        code=code,
        test_list=test_list,
        correct=False,
        error_text=str(e),
        traceback='blah',
    )
