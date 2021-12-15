from django.urls import path

from . import views

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('resume', views.resume, name='resume'),
    path('calendar', views.calendar_webpage, name='calendar_webpage'),
    path('rolls/<int:roll_size>', views.dnd_rolls, name='dnd_rolls'),
    path('rollsapi/<int:roll_size>', views.dnd_rolls_api, name='dnd_rolls_api'),
    path('kky', views.kky_acceptance_page, name='kky_acceptance_page'),
    path('cube_wallpaper/', views.cube_wallpaper, name='cubeWallpaper'),
    path('url_shortener', views.url_shortener, name='urlShortener'),
    path('url_shortener_submit', views.url_shortener_submit, name='urlShortenerSubmit'),
    path('r/<str:shortened_url>', views.redirect_url, name='redirection')
]