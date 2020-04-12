from django.urls import path

from . import views

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('resume', views.resume, name='resume'),
    path('calendar', views.calendar_webpage, name='calendar_webpage'),
    path('rolls/<int:roll_size>', views.dnd_rolls, name='dnd_rolls'),
    path('rollsapi/<int:roll_size>', views.dnd_rolls_api, name='dnd_rolls_api'),
]