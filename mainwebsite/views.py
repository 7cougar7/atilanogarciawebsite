import json
import random
from datetime import datetime

from django.shortcuts import render


def homepage(request):
    context = {
        'title': 'Home Page',
        'content': 'homepage'
    }
    return render(request, 'base.html', context)


def resume(request):
    context = {
        'title': 'Resume',
        'content': 'resume'
    }
    return render(request, 'base.html', context)


def calendar_webpage(request):
    return render(request, 'calendar.html')



def dnd_rolls(request, roll_size):
    random.seed(datetime.now())
    roll_stats = []
    rolls = []
    for x in range(0, roll_size):
        d4 = random.randrange(1, 4, 1)
        d6 = random.randrange(1, 6, 1)
        d8 = random.randrange(1, 8, 1)
        oned10 = random.randrange(1, 10, 1)
        twod10 = random.randrange(1, 10, 1)
        d20 = random.randrange(1, 20, 1)
        total = d4+d6+d8+oned10+twod10+d20
        rolls.append({
            "d4": d4,
            "d6": d6,
            "d8": d8,
            "oned10": oned10,
            "twod10": twod10,
            "d20": d20,
            "total": total
        })
        roll_stats.append({"total": total, "row_number": x+1})
    max_roll = 0
    row_number = 1
    for roll in roll_stats:
        if roll["total"] > max_roll:
            max_roll = roll["total"]
            row_number = roll["row_number"]
    context = {
        'title': 'DND Roller',
        'content': 'roller',
        'rolls': rolls,
        'max_roll': max_roll,
        'row_number': row_number
    }
    return render(request, 'dnd_roll.html', context)
