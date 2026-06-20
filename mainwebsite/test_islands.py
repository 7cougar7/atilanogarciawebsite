"""
Tests for the Vite/React islands integration: the {% vite_asset %} template tag and the
homepage's progressive-enhancement mount points + server-rendered fallback.
"""

import os
from unittest import skipUnless

from django.conf import settings
from django.template import Context, Template
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase, override_settings
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


class ThemeSystemTests(TestCase):
    """The CSS-variable theme: data-theme attribute + React ThemeToggle, no jQuery swap."""

    def setUp(self):
        self.html = self.client.get(reverse("mainwebsite:homepage")).content.decode()

    def test_no_flicker_theme_setter_present(self):
        # The inline script applies the saved theme before paint.
        self.assertIn(
            'document.documentElement.setAttribute("data-theme", "dark")', self.html
        )

    def test_theme_toggle_mount_point_present(self):
        self.assertIn('data-react-component="ThemeToggle"', self.html)

    def test_body_has_themed_fill(self):
        self.assertRegex(self.html, r"<body[^>]*\bclass=\"[^\"]*light-fill")

    def test_old_jquery_swap_removed(self):
        # The class-swapping theme engine and its global switch must be gone.
        self.assertNotIn("switchMode", self.html)
        self.assertNotIn("temp-fill", self.html)
        self.assertNotIn('id="switchButton"', self.html)


class UrlShortenerPageTests(TestCase):
    def setUp(self):
        self.html = self.client.get(
            reverse("mainwebsite:urlShortener")
        ).content.decode()

    def test_mounts_react_island_with_submit_url(self):
        self.assertIn('data-react-component="UrlShortener"', self.html)
        self.assertIn(
            'data-submit-url="%s"' % reverse("mainwebsite:urlShortenerSubmit"),
            self.html,
        )

    def test_server_rendered_fallback_present(self):
        # The form is in the server HTML so the page isn't blank before React mounts.
        self.assertIn("URL To Shorten", self.html)
        self.assertIn("Shorten URL", self.html)

    def test_old_jquery_handlers_removed(self):
        self.assertNotIn("submitForm()", self.html)
        self.assertNotIn("$.ajax", self.html)


class TranslatorPageTests(TestCase):
    def setUp(self):
        self.response = self.client.get(reverse("mainwebsite:translator"))
        self.html = self.response.content.decode()

    def test_page_renders(self):
        # Regression: the old template used a non-namespaced {% url 'start_two_way' %}
        # which raised NoReverseMatch (500). It must reverse and render now.
        self.assertEqual(self.response.status_code, 200)

    def test_mounts_react_island_with_namespaced_submit_url(self):
        self.assertIn('data-react-component="Translator"', self.html)
        self.assertIn(
            'data-submit-url="%s"' % reverse("mainwebsite:start_two_way"),
            self.html,
        )

    def test_old_jquery_handler_removed(self):
        self.assertNotIn("submitForm()", self.html)
        self.assertNotIn("$.ajax", self.html)


class ResumeIslandTests(TestCase):
    def setUp(self):
        self.response = self.client.get(reverse("mainwebsite:resume"))
        self.html = self.response.content.decode()

    def test_mounts_resume_island_with_pdf_url(self):
        self.assertEqual(self.response.status_code, 200)
        self.assertIn('data-react-component="Resume"', self.html)
        self.assertIn("data-pdf-url=", self.html)

    def test_server_rendered_fallback_present(self):
        # Heading + embedded PDF remain in the server HTML for SEO / no-JS.
        self.assertIn("<iframe", self.html)
        self.assertIn(".pdf", self.html)


class GraduationIslandTests(TestCase):
    def setUp(self):
        self.response = self.client.get(reverse("mainwebsite:graduation"))
        self.html = self.response.content.decode()

    def test_mounts_graduation_island_with_image_urls(self):
        self.assertEqual(self.response.status_code, 200)
        self.assertIn('data-react-component="Graduation"', self.html)
        self.assertIn("data-ut-seal=", self.html)
        self.assertIn("data-venmo-logo=", self.html)


class UtilityPagesTests(TestCase):
    def test_404_renders_notfound_island(self):
        # Django runs tests with DEBUG=False, so the handler404 template is used.
        response = self.client.get("/definitely-not-a-real-url/")
        self.assertEqual(response.status_code, 404)
        self.assertIn('data-react-component="NotFound"', response.content.decode())

    def _render(self, template):
        return render_to_string(template, request=RequestFactory().get("/"))

    def test_logged_out_uses_message_card(self):
        html = self._render("logged_out.html")
        self.assertIn('data-react-component="MessageCard"', html)
        self.assertIn("You have been logged out.", html)

    def test_invalid_link_uses_message_card(self):
        html = self._render("magic_link_invalid.html")
        self.assertIn('data-react-component="MessageCard"', html)
        self.assertIn("Invalid Link", html)


class KkyIslandTests(TestCase):
    def setUp(self):
        self.response = self.client.get(reverse("mainwebsite:kky_acceptance_page"))
        self.html = self.response.content.decode()

    def test_mounts_kky_island_with_image_urls(self):
        self.assertEqual(self.response.status_code, 200)
        self.assertIn('data-react-component="Kky"', self.html)
        self.assertIn("data-crest-img=", self.html)
        self.assertIn("data-section-img=", self.html)


class PersonalAiIslandTests(TestCase):
    def test_personal_ai_template_mounts_island(self):
        # Rendered directly (the view itself is passkey-gated); we check the template.
        request = RequestFactory().get("/")
        request.user = type("U", (), {"username": "tilo", "is_authenticated": True})()
        html = render_to_string("personal_ai.html", request=request)
        self.assertIn('data-react-component="PersonalAi"', html)
        self.assertIn("data-username=", html)
        # Regression: must use the namespaced logout URL (bare name raised NoReverseMatch).
        self.assertIn('data-logout-url="%s"' % reverse("mainwebsite:logout"), html)
