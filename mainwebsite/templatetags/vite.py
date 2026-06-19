"""
Minimal Vite integration for Django templates (no third-party dependency).

Production: reads the Vite build manifest (mainwebsite/static/dist/.vite/manifest.json)
and emits <script>/<link> tags whose URLs go through {% static %}, so Django's
ManifestStaticFilesStorage hashing applies on top of Vite's content hashing.

Development: when settings.VITE_DEV_MODE is true, points at the Vite dev server
(settings.VITE_DEV_SERVER_URL) for hot module reloading instead.

A custom tag is used rather than django-vite to avoid adding a Python dependency with
its own Django-version compatibility matrix (the site is on Django 6.0).
"""

import json
import logging
from functools import lru_cache
from pathlib import Path

from django import template
from django.conf import settings
from django.templatetags.static import static
from django.utils.safestring import mark_safe

logger = logging.getLogger(__name__)
register = template.Library()

_DIST_SUBDIR = "dist"
_MANIFEST_PATH = (
    Path(settings.BASE_DIR)
    / "mainwebsite"
    / "static"
    / _DIST_SUBDIR
    / ".vite"
    / "manifest.json"
)


@lru_cache(maxsize=1)
def _load_manifest():
    with open(_MANIFEST_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def _dev_mode():
    return getattr(settings, "VITE_DEV_MODE", False)


def _dev_server():
    return getattr(settings, "VITE_DEV_SERVER_URL", "http://localhost:5173")


@register.simple_tag
def vite_asset(entry="src/main.jsx"):
    """Emit the script/style tags for a Vite entry point."""
    if _dev_mode():
        base = _dev_server()
        return mark_safe(
            f'<script type="module" src="{base}/@vite/client"></script>\n'
            f'<script type="module" src="{base}/{entry}"></script>'
        )

    try:
        manifest = _load_manifest()
        chunk = manifest[entry]
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        # Fail soft but loud: a missing/var build must not 500 every page. The
        # server-rendered fallback inside each island keeps the page functional.
        logger.error(
            "vite_asset: could not resolve entry %r from %s (%s). "
            "Did `npm run build` run before collectstatic?",
            entry,
            _MANIFEST_PATH,
            exc,
        )
        return ""

    tags = []
    for css_file in chunk.get("css", []):
        tags.append(f'<link rel="stylesheet" href="{static(f"dist/{css_file}")}">')
    tags.append(
        f'<script type="module" src="{static(f"dist/{chunk["file"]}")}"></script>'
    )
    return mark_safe("\n".join(tags))
