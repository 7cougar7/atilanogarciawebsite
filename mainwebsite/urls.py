from django.urls import path

from . import views

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('resume', views.resume, name='resume'),
    path('calendar', views.calendar_webpage, name='calendar_webpage')
]