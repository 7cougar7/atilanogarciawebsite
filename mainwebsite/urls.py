from django.urls import path

from mainwebsite import views, views_dnd, twilio_views

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('resume/', views.resume, name='resume'),
    path('calendar/', views.calendar_webpage, name='calendar_webpage'),
    path('rolls/<int:roll_size>/', views_dnd.dnd_rolls, name='dnd_rolls'),
    path('rollsapi/<int:roll_size>/', views_dnd.dnd_rolls_api, name='dnd_rolls_api'),
    path('kky/', views.kky_acceptance_page, name='kky_acceptance_page'),
    path('cube_wallpaper/', views.cube_wallpaper, name='cubeWallpaper'),
    path('url_shortener/', views.url_shortener, name='urlShortener'),
    path('url_shortener_submit/', views.url_shortener_submit, name='urlShortenerSubmit'),
    path('r/<str:shortened_url>/', views.redirect_url, name='redirection'),
    path('graduation/', views.graduation, name='graduation'),
    path('twilio_incoming/', twilio_views.twilio_incoming, name='twilio_incoming'),
    path('twilio_outgoing/', twilio_views.twilio_outgoing, name='twilio_outgoing'),
    path('hello_world/', 'django_twilio.views.say', {
        'text': 'Hello, world! This is just a test of all those crazy test type things'
    }),
]

handler404 = "mainwebsite.views.page_not_found_view"