import json
import logging
import numpy
import requests
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect

from mainwebsite import models

logger = logging.getLogger(__name__)


def page_not_found_view(request, exception):
    return render(request, '404.html', status=404)


def homepage(request):
    context = {
        'title': 'Home Page',
        'content': 'homepage'
    }
    # return render(request, 'base.html', context)
    return render(request, 'homepage.html', context)


def graduation(request):
    context = {
        'title': 'Graduation',
        'content': 'graduation'
    }
    return render(request, 'graduation.html', context)


def cube_wallpaper(request):
    context = {
        'title': 'Cube Wallpaper',
    }
    return render(request, 'cube_wallpaper.html', context)


def resume(request):
    context = {
        'title': 'Resume',
        'content': 'resume'
    }
    return render(request, 'base.html', context)

def linkedin(request):
    return redirect("https://www.linkedin.com/in/atilano-garcia/")

def calendar_webpage(request):
    return render(request, 'calendar.html')


def kky_acceptance_page(request):
    context = {}
    return render(request, 'kky.html', context)


def url_shortener(request):
    return render(request, 'url_shortener.html')


def url_shortener_submit(request):
    if request.method == 'POST':
        url = request.POST['url']
        if url:
            shortened_url = models.ShortenedUrl(real_url=url)
            shortened_url.save()
            return JsonResponse({'shortened_url': request.build_absolute_uri(f"r/{shortened_url.shortened_url}")})
    return JsonResponse({})


def redirect_url(request, shortened_url):
    possible_url = models.ShortenedUrl.objects.filter(shortened_url=shortened_url)
    if possible_url.exists():
        return redirect(possible_url.first().real_url)

def translator(request):
    context = {
        'title': 'Translator',
        'content': 'translator'
    }
    return render(request, 'translator.html', context)