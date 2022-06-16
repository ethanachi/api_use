import json
import os

from .. import task

from . import retrieval
from . import solids

BASE_PATH = 'api_use/api_use_tasks/json_tasks'
for path in os.listdir(BASE_PATH):
    with open(os.path.join(BASE_PATH, path)) as f:
     task.APITask.add_from_json(json.load(f))
