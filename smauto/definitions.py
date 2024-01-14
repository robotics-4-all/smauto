import os
from os.path import dirname, join


THIS_DIR = dirname(__file__)
TEMPLATES_PATH = join(THIS_DIR, "templates")
MODEL_REPO_PATH = os.getenv("SMAUTO_MODEL_REPO", join(THIS_DIR, "builtin_models"))
