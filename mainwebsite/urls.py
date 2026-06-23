from django.urls import path

from mainwebsite import e2e_support, translator_calls, twilio_views, views, views_dnd
from mainwebsite.custom_passkey_views import (
    custom_auth_complete,
    dynamic_auth_begin,
    dynamic_reg_begin,
    dynamic_reg_complete,
)

from .views import MagicLinkVerifyView, UnifiedLoginView

app_name = "mainwebsite"

urlpatterns = [
    path("", views.homepage, name="homepage"),
    path("login/", UnifiedLoginView.as_view(), name="login"),
    path(
        "magic-link-verify/<uidb64>/<token>/",
        MagicLinkVerifyView.as_view(),
        name="magic_link_verify",
    ),
    path("resume/", views.resume, name="resume"),
    path("linkedin/", views.linkedin, name="linkedin"),
    path("calendar/", views.calendar_webpage, name="calendar_webpage"),
    path("rolls/<int:roll_size>/", views_dnd.dnd_rolls, name="dnd_rolls"),
    path(
        "rollsapi/<int:roll_size>/",
        views_dnd.dnd_rolls_api,
        name="dnd_rolls_api",
    ),
    path("kky/", views.kky_acceptance_page, name="kky_acceptance_page"),
    path("cube_wallpaper/", views.cube_wallpaper, name="cubeWallpaper"),
    path("url_shortener/", views.url_shortener, name="urlShortener"),
    path(
        "url_shortener_submit/",
        views.url_shortener_submit,
        name="urlShortenerSubmit",
    ),
    path("r/<str:shortened_url>/", views.redirect_url, name="redirection"),
    path("graduation/", views.graduation, name="graduation"),
    path("translator/", views.translator, name="translator"),
    path(
        "twilio_incoming/",
        twilio_views.twilio_incoming,
        name="twilio_incoming",
    ),
    path(
        "twilio_menu_action/",
        twilio_views.twilio_menu_action,
        name="twilio_menu_action",
    ),
    path("start_two_way/", translator_calls.start_two_way, name="start_two_way"),
    path("set_language/", translator_calls.set_language, name="set_language"),
    path(
        "establish_language_menu/",
        translator_calls.establish_language_menu,
        name="establish_language_menu",
    ),
    path("personal-ai/", views.personal_ai, name="personal_ai"),
    path("intro/", views.intro, name="intro"),
    path("passkeys-register/", views.passkey_register, name="passkey_register"),
    # Custom Passkey URLs
    path(
        "custom/passkeys/reg/begin",
        dynamic_reg_begin,
        name="custom_passkey_reg_begin",
    ),
    path(
        "custom/passkeys/reg/complete",
        dynamic_reg_complete,
        name="custom_passkey_reg_complete",
    ),
    path(
        "custom/passkeys/auth/begin",
        dynamic_auth_begin,
        name="custom_passkey_auth_begin",
    ),
    path(
        "custom/passkeys/auth/complete",
        custom_auth_complete,
        name="custom_passkey_auth_complete",
    ),
    path(
        "logout/",
        views.custom_logout,
        name="logout",
    ),
]

# Dev-only passkey E2E hook (gated behind DEBUG + E2E_TESTING; never present in prod).
if e2e_support.e2e_enabled():
    urlpatterns += [path("_e2e/auth_setup/", e2e_support.auth_setup)]

handler404 = "mainwebsite.views.page_not_found_view"
