"""
Unit tests for the Phase 1 housekeeping changes: the SEO context processor, the
unified base template's analytics handling, and the migrated resume/kky pages.
"""

from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from mainwebsite.context_processors import seo_context


class SeoContextProcessorTests(TestCase):
    def setUp(self):
        self.request = RequestFactory().get("/")

    @override_settings(
        GOOGLE_ANALYTICS_ID="G-TEST123", GOOGLE_SITE_VERIFICATION="verify-abc"
    )
    def test_returns_configured_values(self):
        ctx = seo_context(self.request)
        self.assertEqual(ctx["google_analytics_id"], "G-TEST123")
        self.assertEqual(ctx["google_site_verification"], "verify-abc")

    @override_settings(GOOGLE_ANALYTICS_ID="", GOOGLE_SITE_VERIFICATION="")
    def test_returns_empty_when_unconfigured(self):
        ctx = seo_context(self.request)
        self.assertEqual(ctx["google_analytics_id"], "")
        self.assertEqual(ctx["google_site_verification"], "")

    @override_settings(GOOGLE_ANALYTICS_ID="G-XYZ")
    def test_exposes_exactly_the_seo_keys(self):
        self.assertEqual(
            set(seo_context(self.request)),
            {"google_analytics_id", "google_site_verification"},
        )


class ResumePageTests(TestCase):
    def setUp(self):
        self.url = reverse("mainwebsite:resume")

    def test_renders_resume_template(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "resume.html")
        self.assertTemplateUsed(response, "new_base.html")

    def test_embeds_pdf_and_download_link(self):
        response = self.client.get(self.url)
        self.assertContains(response, "<iframe")
        self.assertContains(response, ".pdf")
        self.assertContains(response, "trackResumeDownload()")


class KkyPageTests(TestCase):
    def setUp(self):
        self.url = reverse("mainwebsite:kky_acceptance_page")

    def test_renders_on_unified_base(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "kky.html")
        self.assertTemplateUsed(response, "new_base.html")

    def test_mounts_kky_react_island(self):
        # The breadcrumb + content are now rendered by the Kky React island, so the
        # server HTML carries the mount point rather than the markup itself.
        response = self.client.get(self.url)
        self.assertContains(response, 'data-react-component="Kky"')


class AnalyticsStubTests(TestCase):
    """The tracking stubs must always be defined so onclick handlers never throw,
    while the real GA snippet appears only when an analytics ID is configured."""

    def setUp(self):
        self.url = reverse("mainwebsite:resume")

    @override_settings(GOOGLE_ANALYTICS_ID="")
    def test_stub_functions_present_without_analytics_id(self):
        response = self.client.get(self.url)
        self.assertContains(response, "function trackResumeDownload()")
        self.assertContains(response, "function trackProjectView(")
        self.assertNotContains(response, "googletagmanager.com/gtag")

    @override_settings(GOOGLE_ANALYTICS_ID="G-REALID")
    def test_real_ga_snippet_present_with_analytics_id(self):
        response = self.client.get(self.url)
        self.assertContains(response, "googletagmanager.com/gtag")
        self.assertContains(response, "G-REALID")

    @override_settings(GOOGLE_SITE_VERIFICATION="verify-token-xyz")
    def test_site_verification_meta_rendered_when_set(self):
        response = self.client.get(self.url)
        self.assertContains(response, "verify-token-xyz")

    @override_settings(GOOGLE_SITE_VERIFICATION="")
    def test_site_verification_meta_absent_when_unset(self):
        response = self.client.get(self.url)
        self.assertNotContains(response, 'name="google-site-verification"')
