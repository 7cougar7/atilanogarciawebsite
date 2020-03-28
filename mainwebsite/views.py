from django.shortcuts import render


def homepage(request):
    context = {'test': 'homepage'}
    return render(request, 'base.html', context)


def resume(request):
    context = {'test': 'resume'}
    return render(request, 'base.html', context)
