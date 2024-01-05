from django.urls import path

from mainwebsite import views, views_dnd, twilio_views, translator_calls

urlpatterns = [
    path(r"", views.homepage, name="homepage"),
    path(r"resume/", views.resume, name="resume"),
    path(r"linkedin/", views.linkedin, name="linkedin"),
    path(r"calendar/", views.calendar_webpage, name="calendar_webpage"),
    path(r"rolls/<int:roll_size>/", views_dnd.dnd_rolls, name="dnd_rolls"),
    path(
        r"rollsapi/<int:roll_size>/",
        views_dnd.dnd_rolls_api,
        name="dnd_rolls_api",
    ),
    path(r"kky/", views.kky_acceptance_page, name="kky_acceptance_page"),
    path(r"cube_wallpaper/", views.cube_wallpaper, name="cubeWallpaper"),
    path(r"url_shortener/", views.url_shortener, name="urlShortener"),
    path(
        r"url_shortener_submit/",
        views.url_shortener_submit,
        name="urlShortenerSubmit",
    ),
    path(r"r/<str:shortened_url>/", views.redirect_url, name="redirection"),
    path(r"graduation/", views.graduation, name="graduation"),
    path(r"translator/", views.translator, name="translator"),
    path(
        r"twilio_incoming/",
        twilio_views.twilio_incoming,
        name="twilio_incoming",
    ),
    path(
        r"twilio_menu_action/",
        twilio_views.twilio_menu_action,
        name="twilio_menu_action",
    ),
    path(r"start_two_way/", translator_calls.start_two_way, name="start_two_way"),
    path(r"set_language/", translator_calls.set_language, name="set_language"),
    path(
        r"establish_language_menu/",
        translator_calls.establish_language_menu,
        name="establish_language_menu",
    ),
]

handler404 = "mainwebsite.views.page_not_found_view"
