from django.shortcuts import render


def homepage(request):
    context = {
        'title': 'Home Page',
        
        'test': 'homepage'
    }
    return render(request, 'base.html', context)


def resume(request):
    context = {
        'title': 'Resume',
        'test': 'resume'
    }
    return render(request, 'base.html', context)


def calendar_webpage(request):
    return render(request, 'calendar.html')
