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

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from mainwebsite.custom_passkey_views import (
    custom_auth_complete,
    dynamic_auth_begin,
    dynamic_reg_begin,
    dynamic_reg_complete,
)

urlpatterns = [
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
    # Custom logout URL that redirects to the passkey login page
    path(
        "logout/",
        auth_views.LogoutView.as_view(next_page="passkey_login"),
        name="logout",
    ),
]
