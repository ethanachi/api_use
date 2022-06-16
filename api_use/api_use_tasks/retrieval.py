from .. import task
from .. import utils

retrieval = {
  'chem': {
    'container': 'molecule',
    'element': 'atom',
    'attributes': ["atomic_num", "atomic_weight", "quantum_number", "electronegativity", "ionization_energy", "affinity"]
  },
  'music': {
    'container': 'melody',
    'element': 'note',
    'attributes': ["pitch", "volume", "velocity", "articulation", "length", "tuning"]
  },
}

for retrieval_id, retrieval_data in retrieval.items():
  attributes = retrieval_data['attributes']
  container = retrieval_data['container']
  element = retrieval_data['element']

  parent_defns = [
    [f"get_atom_with_{attr}", f"Returns {utils.an(element)} in the {container} with [{utils.spacify(attr)}|attr].", [attr], "atom"]
    for attr in attributes
  ]
  child_defns = [
    [f"get_{attr}", f"Returns the {utils.spacify(attr)} of the {element}.", [], "float"]
    for attr in attributes
  ]

  task.APITask.add_to_registry(id=container,
                          library_name=container,
                          functions=parent_defns,
                          style='class')

  task.APITask.add_to_registry(id=element,
                          library_name=element,
                          functions=child_defns,
                          style='class')
