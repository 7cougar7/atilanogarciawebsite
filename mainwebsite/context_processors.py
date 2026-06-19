from django.conf import settings


def seo_context(request):
    return {
        "google_analytics_id": settings.GOOGLE_ANALYTICS_ID,
        "google_site_verification": settings.GOOGLE_SITE_VERIFICATION,
    }
