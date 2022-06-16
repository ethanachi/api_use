
from .. import task
from .. import utils

## Shapes of various dimensions

dimension_data = {
  1: {
    'solids': ["tetrahedron", "cube", "octahedron", "sphere", "prism"],
    'arglist': ['radius'],
  },
  2: {
    'solids': ["cylinder", "capsule", "cone", "prism", "parallelepiped"],
    'arglist': ['radius', 'height'],
  },
  3: {
    'solids': ["cylinder", "capsule", "cone", "prism", "parallelepiped"],
    'arglist': ['length', 'width', 'height'],
  },
  4: {
    'solids': ["cylinder", "capsule", "cone", "prism", "parallelepiped"],
    'arglist': ['length', 'width', 'height', 'depth'],
  },
}


for dimension in range(1, 5):
  data = dimension_data[dimension]

  defns = []
  params = utils.andjoin((f'[{arg}|{arg}]' for arg in data['arglist']))
  for feature in ("volume", "surface_area"):
    for solid in data['solids']:
      defns.append([f"{feature}_of_{solid}", f"Calculates the {utils.spacify(feature)} of a {solid} with {params}.", data['arglist'], 'float'])

  task.APITask.add_to_registry(id=f"solids{dimension}",
                          library_name="solids",
                          functions=defns,
                          style='import')
  if dimension == 2:
    task.APITask.add_to_registry(id=f"solids",
                            library_name="solids",
                            functions=defns,
                            style='import')
