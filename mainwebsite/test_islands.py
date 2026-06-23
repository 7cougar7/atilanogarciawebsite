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

    def test_hero_mount_point_present(self):
        self.assertIn('data-react-component="Hero"', self.html)

    def test_old_homepage_islands_removed(self):
        # The v2 homepage server-renders work/contact directly; the old ProjectList and
        # SocialLinks islands (and their json_script props) are gone.
        self.assertNotIn('data-react-component="ProjectList"', self.html)
        self.assertNotIn('data-react-component="SocialLinks"', self.html)
        self.assertNotIn('id="projectlist-props"', self.html)

    def test_server_rendered_content_for_seo(self):
        # Project names and social icons are in the server HTML (no-JS / SEO).
        for project in PROJECTS:
            self.assertIn(project["name"], self.html)
        for social in SOCIALS:
            self.assertIn(social["icon"], self.html)


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

    def test_body_has_v2_class(self):
        self.assertRegex(self.html, r"<body[^>]*\bclass=\"v2")

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
        self.assertIn("URL to shorten", self.html)
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


class ResumePageTests(TestCase):
    def setUp(self):
        self.response = self.client.get(reverse("mainwebsite:resume"))
        self.html = self.response.content.decode()

    def test_renders_styled_resume_not_pdf_embed(self):
        # The résumé is now rendered as styled HTML (no PDF iframe / React island).
        self.assertEqual(self.response.status_code, 200)
        self.assertNotIn("<iframe", self.html)
        self.assertNotIn('data-react-component="Resume"', self.html)

    def test_content_and_pdf_download_present(self):
        # Section content for SEO / no-JS, plus a PDF download link.
        self.assertIn("Technical Experience", self.html)
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
    def test_404_renders_v2_error_page(self):
        # Django runs tests with DEBUG=False, so the handler404 template is used.
        response = self.client.get("/definitely-not-a-real-url/")
        self.assertEqual(response.status_code, 404)
        html = response.content.decode()
        self.assertIn(">404<", html)
        self.assertIn("Back home", html)

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


class AuthPagesTests(TestCase):
    def test_login_mounts_unified_login_island(self):
        html = self.client.get(reverse("mainwebsite:login")).content.decode()
        self.assertIn('data-react-component="UnifiedLogin"', html)
        self.assertIn(
            'data-auth-begin-url="%s"'
            % reverse("mainwebsite:custom_passkey_auth_begin"),
            html,
        )

    def test_passkey_register_template_mounts_island(self):
        # The view is magic-link-gated; check the template renders the island.
        html = render_to_string(
            "passkey_register.html", request=RequestFactory().get("/")
        )
        self.assertIn('data-react-component="PasskeyRegister"', html)
        self.assertIn(
            'data-reg-begin-url="%s"' % reverse("mainwebsite:custom_passkey_reg_begin"),
            html,
        )
