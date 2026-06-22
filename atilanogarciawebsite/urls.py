"""atilanogarciawebsite URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

import os

from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse
from django.shortcuts import redirect
from django.templatetags.static import static
from django.urls import include, path
from django.utils import timezone

from mainwebsite.custom_passkey_views import (
    custom_auth_complete,
    dynamic_auth_begin,
    dynamic_reg_begin,
    dynamic_reg_complete,
)
from mainwebsite.views import custom_logout


def favicon_ico(request):
    """Redirect the browser's default /favicon.ico request to the static icon
    (resolved per-request so it picks up the hashed name in production)."""
    return redirect(static("mainwebsite/img/logo/new/favicon.ico"))


def robots_txt(request):
    """Serve robots.txt file"""
    robots_path = os.path.join(settings.BASE_DIR, "robots.txt")
    try:
        with open(robots_path, "r") as f:
            content = f.read()
        return HttpResponse(content, content_type="text/plain")
    except FileNotFoundError:
        return HttpResponse("User-agent: *\nAllow: /", content_type="text/plain")


def sitemap_xml(request):
    """Generate XML sitemap dynamically"""
    base_url = f"https://{request.get_host()}"
    current_date = timezone.now().strftime("%Y-%m-%d")

    # Define your main pages with their priorities and change frequencies
    urls = [
        {"loc": "/", "priority": "1.0", "changefreq": "weekly"},
        {"loc": "/graduation/", "priority": "0.8", "changefreq": "monthly"},
        {"loc": "/translator/", "priority": "0.7", "changefreq": "monthly"},
        {"loc": "/url-shortener/", "priority": "0.6", "changefreq": "monthly"},
        {"loc": "/intro/", "priority": "0.5", "changefreq": "monthly"},
        {"loc": "/cube-wallpaper/", "priority": "0.5", "changefreq": "monthly"},
    ]

    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">"""

    for url_info in urls:
        xml_content += f"""
    <url>
        <loc>{base_url}{url_info['loc']}</loc>
        <lastmod>{current_date}</lastmod>
        <changefreq>{url_info['changefreq']}</changefreq>
        <priority>{url_info['priority']}</priority>
    </url>"""

    xml_content += """
</urlset>"""

    return HttpResponse(xml_content, content_type="application/xml")


urlpatterns = [
    path("favicon.ico", favicon_ico, name="favicon_ico"),
    path("robots.txt", robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap_xml, name="sitemap_xml"),
    path("admin/", admin.site.urls),
    path("", include("mainwebsite.urls")),
    # Override django-passkeys URLs with our custom dynamic views
    path("passkeys/reg/begin", dynamic_reg_begin, name="passkeys_reg_begin"),
    path(
        "custom/passkeys/reg/complete",
        dynamic_reg_complete,
        name="custom_passkeys_reg_complete",
    ),
    path("passkeys/auth/begin", dynamic_auth_begin, name="passkeys_auth_begin"),
    path("passkeys/auth/complete", custom_auth_complete, name="passkeys_auth_complete"),
    # Include the rest of the passkeys URLs
    path("passkeys/", include("passkeys.urls")),
    # Custom logout URL that redirects to the unified login page
    path(
        "logout/",
        custom_logout,
        name="logout",
    ),
]
