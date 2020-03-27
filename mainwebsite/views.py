from django.shortcuts import render
from django.http import HttpResponse

def index(request):
    return HttpResponse("Hello world. You're at the main landing page 123 Test :)")


