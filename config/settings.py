import os
from decouple import config

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

from .settings.dev import *
