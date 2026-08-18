"""Entrypoint WSGI usado pela Vercel (runtime @vercel/python).

Todas as rotas são redirecionadas para cá via vercel.json, e a Vercel
espera encontrar uma variável de módulo chamada `app` (WSGI callable).
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.wsgi import get_wsgi_application  # noqa: E402

app = get_wsgi_application()
