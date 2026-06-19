"""
Tests for the Vite/React islands integration: the {% vite_asset %} template tag and the
homepage's progressive-enhancement mount points + server-rendered fallback.
"""

import os
from unittest import skipUnless

from django.conf import settings
from django.template import Context, Template
from django.test import TestCase, override_settings
from django.urls import reverse

from mainwebsite.site_content import PROJECTS, SOCIALS

# The Vite bundle is built on demand (not committed), so tests that assert the real
# bundle renders only run when a build is present. Everything else (dev mode, fail-soft,
# server-rendered fallback, mount points) is build-independent and always runs.
_MANIFEST = os.path.join(
    settings.BASE_DIR, "mainwebsite", "static", "dist", ".vite", "manifest.json"
)
_HAS_BUILD = os.path.exists(_MANIFEST)
_NEEDS_BUILD = skipUnless(_HAS_BUILD, "frontend not built (run `npm run build`)")


def render_tag(snippet, context=None):
    return Template("{% load vite %}" + snippet).render(Context(context or {}))


class ViteAssetTagTests(TestCase):
    @_NEEDS_BUILD
    def test_production_emits_hashed_bundle_script(self):
        html = render_tag("{% vite_asset %}")
        self.assertIn('<script type="module"', html)
        # Points at the built bundle, routed through {% static %} hashing.
        self.assertIn("dist/assets/main-", html)
        self.assertIn(".js", html)

    @override_settings(VITE_DEV_MODE=True, VITE_DEV_SERVER_URL="http://localhost:5173")
    def test_dev_mode_points_at_vite_server(self):
        html = render_tag("{% vite_asset %}")
        self.assertIn("http://localhost:5173/@vite/client", html)
        self.assertIn("http://localhost:5173/src/main.jsx", html)

    def test_missing_entry_fails_soft(self):
        # A bogus entry must not raise (would 500 the page); returns empty instead.
        html = render_tag("{% vite_asset 'src/does-not-exist.jsx' %}")
        self.assertEqual(html.strip(), "")


class HomepageIslandsTests(TestCase):
    def setUp(self):
        self.response = self.client.get(reverse("mainwebsite:homepage"))
        self.html = self.response.content.decode()

    def test_page_ok(self):
        self.assertEqual(self.response.status_code, 200)

    @_NEEDS_BUILD
    def test_bundle_loaded(self):
        self.assertRegex(
            self.html,
            r'<script type="module" src="[^"]*dist/assets/main-[^"]+\.js"',
        )

    def test_props_json_scripts_present(self):
        self.assertIn('id="projectlist-props"', self.html)
        self.assertIn('id="sociallinks-props"', self.html)

    def test_mount_points_present(self):
        # Project list is shown in both the desktop and mobile columns.
        self.assertEqual(self.html.count('data-react-component="ProjectList"'), 2)
        self.assertEqual(self.html.count('data-react-component="SocialLinks"'), 1)

    def test_server_rendered_fallback_for_seo(self):
        # Every project label and social platform is in the server HTML (no-JS / SEO).
        for project in PROJECTS:
            self.assertIn(project["label"], self.html)
        for social in SOCIALS:
            self.assertIn(social["icon"], self.html)

    def test_analytics_hooks_preserved(self):
        self.assertIn("trackProjectView(", self.html)
        self.assertIn("trackSocialClick(", self.html)
