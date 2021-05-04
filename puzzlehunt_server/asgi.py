"""
ASGI config
"""

import os
import django
from channels.routing import get_default_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "puzzlehunt_server.settings.local_settings")
django.setup()
application = get_default_application()
