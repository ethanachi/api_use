# API Use Benchmark


[Try the demo Colab: <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/>](https://colab.research.google.com/github/ethanachi/api_use/blob/main/demo_colab.ipynb)

The **Synthetic API Use** package aims to evaluate large language models (LLMs)' ability to
perform tool use during code generation.
Standard analysis of this nature is confounded by **memorization**--On one hand, common "coding
interview"-type questions, which one might expect to require extensive compositional reasoning, are
surprisingly easy to solve for language models, while on the other hand, LLMs can
often struggle given a less common but perfectly reasonably formulated question, instead providing
answers to a more common prompt (Figure 1).

This package enables sidestepping these questions through by evaluating models on \textit{synthetic} programming problems.
Each of our generated problems relies upon \textbf{synthetic libraries}: end-user-defined Python libraries with no actual code definitions, merely natural-language documentation.

The benchmark consists of synthetic API's: synthetic Python libraries,
each of which tests various facets of reasoning in code synthesis. 
An accompanying Python testbed generates **programming problems** which must be
solved using functions from these synthetic API's.
At evaluation time, a large language model is first presented with the definition of the API(s),
then prompted to complete the programming problem using the functions it has seen.

## Synthetic API's

For the purpose of constructing API use problems,
we define the concept of a **synthetic library** (or synthetic API).
These libraries do not actually exist as fleshed-out Python code:
rather, they consist solely of function signatures accompanied by natural-language definitions.
Importantly, the function definitions are typed internally; this allows our package to compute appropriate references for chained, nested, or composed function calls.

We provide a set of synthetic libraries upon which we construct our benchmarks.
In addition to these provided API's, benchmark end users can also define their own API's.
This can be done either declaratively (through JSON) or programmatically (through a Python interface).


| Library | Task | Example call |
| --- | --- | --- |
| Image manipulation | Manipulating images, PIL-style | `image.rotate(45).blur()` |
| Chemistry   | Manipulating and searching through molecules | `molecule.get_atom_with_atomic_weight(75).get_label()`
| Music | Searching through songs and melodies for notes and converting them to other formats | `melody.get_note_with_pitch("A").to_midi()`
| Solids | Computing physical attributes of *n*-dimensional solids | `solids.get_volume_of_cylinder(5, 2, 3)`

Libraries are defined by a class of type `tasks.APITask` and are stored in the
`APITask` registry. At minimum, a library contains a list of functions, each
containing a function name, documentation for that function (in English), a list
of arguments, and a return type. Here's a representative example from the
`image` library:

```json
[
  {
    "function_name": "rotate",
    "documentation": "Returns the image rotated by the given number of degrees",
    "arglist": ["degrees"],
    "return_type": ["image"]
  },
  {
    "function_name": "flip_horizontal",
    "documentation": "Returns the image flipped horizontally",
    "arglist": [""],
    "return_type": ["image"]
  },
  {
    "function_name": "get_width",
    "documentation": "Returns the width of the image",
    "arglist": [],
    "return_type": ["int"]
  }
]
```

This instantiates three functions: `image.rotate(degrees) -> image`,
`image.flip_horizontal() -> image`, and `image.get_width() -> int`. Libraries
can be instantiated in either Python or JSON.

## Synthetic Problems

Creating a programming problem requires two arguments:

- the **function signature**, a call (or composition of calls) to function(s) from one or more Synthetic API's
- the **description**, a specification in plain English of what the function signature does

Solving the resulting problem requires, given the description, generating code *equivalent* to the function signature.
Specifically, the generated code must follow the same control flow and arguments as the reference solution.

### Generation

To generate a programming problem, call **`api_use.get_example(signature, description)`**:

```python
results = get_example(
  signature='solids.volume_of_cone()',
  description='gets the volume of a cone',
)
```


This returns an `api_use.TestCase` object with three fields:

-   `.prompt`: English text which presents the API and gives the function to be written. You should pass this to the model being
    evaluated as the prefix for generation.

```python
>>> print(results.prompt)
"""Consider the following functions:
def solids.volume_of_cone(radius, height):
    Calculates the volume of a cone with the given radius and the given height.

Write a function that gets the volume of a cone.
[BEGIN]
import solids
def test(radius, height):
    """
```

-   `.target`: the correct answer to the problem. You don't need this string to
    evaluate model performance, but it's helpful to examine the correct answer.

<!--```python
>>> print(results.target)
"""return solids.volume_of_cone("dummy_radius_0", "dummy_height_1")"""
```-->

-   `.test`: A piece of code that can be used to verify the answer to this
    problem.

<!--```python
>>> print(results.test)
"""# signature = def test(radius, height):
# indent = '    '
solids = Dummy()
x = test(radius="dummy_radius_0", height="dummy_height_1")
y = solids.volume_of_cone("dummy_radius_0", "dummy_height_1")
assert x == y, f'Test failure: {x} != {y}"""
```-->


### Evaluation

To test whether a sample from a model passes a programming problem,
call `api_use.execute(sample, test)`, which returns a tuple containing whether
the test passed and the error message, if any.

```python
>>> sample = sample_from_my_model(prefix=results.prompt)
>>> is_correct, error_message = api_use.execute(sample, results.test)
(True, None)
```

### Customizing programming problems

The difficulty of code synthesis can be affected by a variety of factors.
The dependence of model reasoning on these factors can be probed by dialling various
attributes of the programming problem.
programming problem can be customized by passing configuration
arguments to the `get_example` function, as described below.

Examples of dialling all of these features—and many more—are in the [Colab](#).

| Library | Task | `get_example()` arg | Benchmark file |
| --- | --- | --- | --- |
| **Distractors** |  When presented with a large number of functions from the same API, can models still select the correct function to complete a task? | `n_distractors` | `tests/distractors_positioning.json` |
| **Semantic invariance** | When reading documentation, do models base their decisions off the function name, the function description, or both? | `func_noise` | `tests/semantic_invariance.json` |
| **Order invariance** | Can models flexibly work with argument order, passing arguments to an API in a different order or with a different degree of specification compared to the input? | `arg_order` | `tests/argument_fixing.json` |
| **Compositionality** |  Can models effectively compose functions, using the output of one function call as the input to the next? To what extent do the *length* and the *width* of this chain affect generation correctness? | Specify composition in `signature` | `tests/chaining.json` |
| **Formatting** | Do small differences in formatting affect model ability to generate correct code? | Numerous; see Formatting section... | (no test yet) |

# Benchmarks

For convenience, we also provide benchmark files in `tests/`.
Each benchmark file specifies the arguments to produce a series of test which combined, plot model performance against a model against
a particular dial. 

To visualize examples from a benchmark file:

```bash
python3 -m api_use.visualize tests/distractors_and_positioning.json
```
To evaluate a model against a programming problem:

```bash
python3 evaluate.py testcases/distractors_and_positioning.json \
--model_type codex \
--rpn cushman
```

Currently, we support decoding from OpenAI's GPT-3-like language models (i.e. Codex). Please consult `evaluate.py` for more information.

# API Reference

<!-- [TODO] Don't gear towards person who is CREATING new libraries,
gear towards person who is running experiments at the highest level. -->

## Libraries

All test examples are drawn from **libraries**; each library defines sets of
functions from which tests can be drawn. For example, to test a model's ability
to perform image manipulation, one might draw from image processing functions
defined in the `image` library.

(Note: Each Synthetic API has an unique label, e.g. `solids2`; optionally, the actual name for the library in code can be different (e.g. `solids`.))

### Types of libraries

\paragraph{Library types} We support two related but similar kinds of synthetic libraries, corresponding to two major kinds of API's commonly found in Python code. **Importable** libraries are typically imported at the top level, providing global-level functions (e.g. `random` or `re`). **Class** libraries are used as the instance of a class, providing member functions which operate on some object.
As the underlying code supporting these libraries is identical, objects from each kind of library can be chained with each other.

```python
# importable library
import solids
print(solids.get_volume_of_sphere(radius=5))

# class library
image = Image()
print(image.flip_horizontal().blur())
```

Since calling these two kinds of objects in Python is similar, we mostly reuse
code between the two cases. Each library defines itself whether it is an
importable or class library.

When building programming problems, an importable library can return objects of a class
library type, which can then have functions called on it. Similarly, objects of
a class library type can be provided as arguments to functions from an
importable library.

## Building programming problems

The core of the API Use benchmark is a **programming problem**: a definition of one or
more API's, plus a prompt that describes the function to be completed by the
model which utilizes the previously defined API's. Given a set of libraries in
the `APITask` registry, programming problems can be generated using the
`api_use.get_example()` function. The minimum requirements to generate a test
case are as follows:

-   **`signature`**: The **function signature**, a function call (or arbitrarily
    nested combination of function calls) to be replicated as part of the test.
    Calls must be of the form `library.signature(...)` where `library` is a
    Synthetic API previously defined in the `APITask` registry. 
-   **`description`**: Documentation for the function to be written The model
    will use this description to reconstruct the corresponding function
    signature.
-   **`func_name`**: A name for the function to be written.

Here's an example:

```python
api_use.get_example(signature="solids.volume_of_cone()",
                   description="gets the volume of a cone",
                   func_name="get_volume_of_cone")
```

By default, this produces the following output:

```
Consider the following functions:

def solids.volume_of_cone(radius, height):
    Calculates the volume of a cone with the given radius and height.

Write a function that computes the volume of a cone given its radius and height.
[BEGIN]
import solids
def get_volume_of_cone(radius, height):
```

To view the corresponding programming problem, pass the `return_test_case=True` argument.


## Dialing attributes

One major advantage of synthetically generating problems is *controllability*: an end user can tightly control all characteristics of a generated problem.
Examining programming problems drawn from real-life sources, 
even problems that use similar skills or forms of reasoning may differ significantly in their use of memorization, involvement of other form of reasoning, or a generally different problem structure.
The lack of a minimal pair between problems thus makes it difficult to make a strong causal statement about the interaction between factors of reasoning and model performance.
By contrast, our synthetic API use problems are designed to allow for the easy creation of minimal pairs.
Our package exposes a large number of parameters, most of which correspond to some factor of the reasoning process.
Therefore, by modifying one or more of these parameters, one can create a minimal pair, benchmarking a model against two variants of the same problem and understanding the causal influence of problem characteristics on model performance.

#### Few-shot prompting

We support few-shot prompting through the `fewshot` parameter:
simply pass the arguments for each few-shot example as a dictionary.
These arguments will be forwarded to create a series of (completed) few-shot examples.
All functions used in all few-shot examples, plus the main prompt's list of functions, are combined into one function list.

#### Composition

Requiring models to use multiple functions and connect their results to each
other tests their ability to perform **composition**, a core part of reasoning.
The benchmark supports generating programming problems with arbitrary composition; simply
pass a function composition as the `signature`. The results of one function can
be passed as an argument to another function:

```python
  image.rotate(pixels=image.get_width())
```

or as the subject of another function call.

```python
  molecule.get_atom_with_atomic_num(55).get_atomic_weight()
```

In this second case, the return type of the first function call is used to
disambiguate the library for the next function call. For example, in the below
example the return type of `get_atomic_with_atomic_num` in library `molecule` is
defined to be `atom`, so the `atom.get_atomic_weight()` function is used.

Multiple levels of composition are possible:

```python
  image.rotate_right(5).rotate_left(5).rotate_right(image.get_width())
```

#### Argument order

Synthesizing full-featured programs necessarily requires the ability to work with \textit{subroutines}, or dependent function calls.
Passing data to such subroutines requires a flexible handling of data flow:
not all data in the global scope will be passed to a subroutine, 
while additional arguments may need to be computed.
Those arguments that are passed may be in a different order from the global scope.
Successfully working with subroutines, then, requires learning an equivalence between \textit{outer} function arguments---the arguments to the outer function to be synthesized---and \textit{inner} function arguments---the arguments to the subroutine itself.

We view the process of calling and working with synthetic API's as an effective testing ground for evaluating LLM understanding of this equivalence. 
Our generated programming problems expose multiple ways to modify the standard outer-inner argument correspondence.
Specifically, our package supports the following options; each option can be configured through simple modifications to the function signature
(Figure \ref{fig:argument_order}).


-   **Fixing arguments**: Any inner API call arguments can be *fixed*—set to constant values—by specifying the key and value appropriately in the function
    signature:

```python
# Fixing no arguments
api_use.get_example(signature="solids.volume_of_cylinder()",
                   description="gets the volume of a cylinder",
                   func_name="get_volume_of_cylinder")
# Output:
Write a function that gets the volume of a cylinder.
def get_volume_of_cylinder(radius, height):
⌶
```

```python
# Fixing first argument
api_use.get_example(signature="solids.volume_of_cylinder(radius=5)",
                   description="gets the volume of a cylinder with radius 5",
                   func_name="get_volume_of_cylinder_radius_5")
# Output:
Write a function that gets the volume of a cylinder.
def get_volume_of_cylinder_with_radius_5(height):
⌶
```

Additionally, the arguments can be fixed in arbitrary order:

```python
# Fixing both arguments in reverse order
api_use.get_example(signature="solids.volume_of_cylinder(height=4, radius=5)",
                   description="gets the volume of a cylinder with height 4 and radius 5",
                   func_name="get_volume_of_cylinder_with_height_4_radius_5")
# Output:
Write a function that gets the volume of a cylinder with height 4 and radius 5.
def get_volume_of_cylinder_with_height_4_radius_5():
⌶
```

-   **Outer argument order**: The *outer* arguments---the arguments to the function to be synthesized---must correspond to all unfixed arguments to API calls within the function. 
However, these outer arguments can be in any order---
for example, given a synthetic API function `solids.volume\_of\_cone(height, radius)`, one could create a problem which tests the ability of a LLM to compute the volume of a cone given its radius and height, i.e. in the opposite order from the API---
and be named differently.
Solving the resulting programming problem requires a LLM to understand which API arguments are equivalent to the outer arguments.

By default, the arguments are listed in the order
    they appear in the signature:

```python
def image.rotate(degrees):
    Returns the image rotated by the given number of degrees.
def image.blur(pixels):
    Returns the image blurred by the given number of pixels.

# Task signature:
{
    "signature": "image.rotate().blur()"
    "func_name": "rotate_then_blur"
}

# Function output
def rotate_then_blur(image, degrees, pixels):
⌶
```

This can be modified by providing a signature to the **outer function name**:

```python
def image.rotate(degrees):
    Returns the image rotated by the given number of degrees.
def image.blur(pixels):
    Returns the image blurred by the given number of pixels.

# Task signature:
{
    "signature": "image.rotate().blur()"
    "func_name": "rotate_then_blur(image, pixels, degrees)"
}

# Function output
def rotate_then_blur(image, pixels, degrees):
⌶
```

```python
def image.rotate(degrees):
    Returns the image rotated by the given number of degrees.
def image.blur(pixels):
    Returns the image blurred by the given number of pixels.

# Task signature:
{
    "signature": "image.rotate(pixels=arg1).blur(degrees=arg2)"
    "func_name": "rotate_then_blur(image, pixels, degrees)"
}

# Function output
def rotate_then_blur(image, arg1, arg2):
⌶
```



### Synthetic API Documentation

**Distractors:**  By default, only those functions called as part of the signature are added to the documentation block; however, this makes selecting the correct function to be used trivial.
To make the function-selection task more challenging, an arbitrarily large number of distractor functions can be added.
These distractor functions are randomly sampled from the corresponding synthetic libraries from which the original functions called are drawn.
The position of the target function within these distractors can also be customized, in order to probe for the existence of either recency or primacy bias.

For each library in the programming problem, distractors are sampled from the set of
functions not evaluated in the programming problem.

-   **Number of distractors** (`num_distractors : Union[int, Dict[str, int]]`):
    -   If an `int`, samples a total of `num_distractors` distractors. The
        distractors are sampled randomly from each library used in the task,
        weighted by the number of times each library is used in the signature.
    -   If a `Dict[str: int]`, samples `num_distractors[library]` distractors
        for each `library`.
-   **Position of target function** (`target_func_location : int = -1`)
    -   By default (if `-1`), spaces the functions evenly in the list of
        confounders.
    -   If an `int` and a single function is used in the programming problem, inserts that
        function at the given index. If multiple functions are used in the test
        case, throws an error.
    -   If a `float` and a single function is used in the programming problem, inserts
        that function at the closest approximate fractional location (e.g.
        `0.5` = halfway through the list of functions). If multiple functions
        are used in the programming problem, throws an error.
    -   If a `Dict[str : int]`, inserts a given function `function_name` at
        index `target_func_location[function_name]`.
    -   If a `Dict[str : float]`, inserts a given function `function_name` at
        fractional index `target_func_location[function_name]`.
        
-   **Function name noise (`function_noise_type : Literal['swap', 'number', 'none'] = 'none'`)**:
     Controls noising of the function names. If `number`, renames all functions to `func1, func2, func3`... etc.
     If `swap`, randomly scrambles all functions in the list of function names so that no function retains its original name.

-   **Description name noise (`desc_noise_type : Literal['swap', 'empty', 'none'] = 'none'`)**:
      Controls noising of the function description names. If `swap`, scrambles all function descriptions so that no function retains its original description.
      If `empty`, no function descriptions are used at all.      

-   **Argument noise type (`arg_noise_type : Literal['number', 'none'] = 'none'`)**:
    Controls noising of the function description names. If `number`, renumbers arguments from 1 onwards (e.g. `arg1`, `arg2`...)

### Formatting

-   **Global indent** (`indent : int = 4`): Controls the indent for all Python
    code + descriptions.
-   **Intro** (`task_description_preamble : str = "Consider the following
    functions:"`): the introductory sentence that goes before the list of
    functions.
-   **Function description**: By default, documentation is on a new line,
    indented. This can be modified with the following arguments:
    -   `use_quotes : bool = False`: If `True`, inserts triple-quotes around
        each function to more resemble a function definition.

```python
def solids.volume_of_cone(radius, height):
    """Calculates the volume of a cone with the given radius and height."""
```

-   `format_function : Callable`: If this argument is provided, it will be used
    to format each function. Example:

```python
def ff(func):
    args = func.args
    arglist = ", ".join(args)
    return f"- {func.library_name}.{func.name}({arglist}): {func.definition}"

view(api_use.get_example(signature="solids.volume_of_cone()",
                         description="gets the volume of a cone",
                         func_name="get_volume_of_cone",
                         num_distractors=4,
                         format_function=ff)]

# Output:
Consider the following functions:

- solids.volume_of_parallelepiped(radius, height): Calculates the volume of a parallelepiped with the given radius and height.
- solids.surface_area_of_prism(radius, height): Calculates the surface area of a prism with the given radius and height.
- solids.volume_of_cone(radius, height): Calculates the volume of a cone with the given radius and height.
- solids.surface_area_of_cone(radius, height): Calculates the surface area of a cone with the given radius and height.
- solids.surface_area_of_parallelepiped(radius, height): Calculates the surface area of a parallelepiped with the given radius and height.

Write a function that gets the volume of a cone.
[BEGIN]
import solids
def get_volume_of_cone(radius, height):
```

-   **Preamble joiner (`joiner : str = '\n`)**: Controls the separator between each
    function definition. By default, this is a single newline.
