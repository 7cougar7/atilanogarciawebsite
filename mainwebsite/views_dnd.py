import numpy
import requests
from django.shortcuts import render

def dnd_rolls(request, roll_size):
    numpy.random.seed()
    d4 = numpy.random.randint(1, 5, roll_size)
    d6 = numpy.random.randint(1, 7, roll_size)
    d8 = numpy.random.randint(1, 9, roll_size)
    oned10 = numpy.random.randint(1, 11, roll_size)
    twod10 = numpy.random.randint(1, 11, roll_size)
    d12 = numpy.random.randint(1, 13, roll_size)
    d20 = numpy.random.randint(1, 21, roll_size)
    total = numpy.sum([d4, d6, d8, oned10, twod10, d12, d20], axis=0)
    max_roll = numpy.amax(total)
    row_number = numpy.where(total == numpy.amax(total))[0]
    context = {
        'title': 'DND Roller',
        'content': 'roller',
        'd4': d4,
        'd6': d6,
        'd8': d8,
        'oned10': oned10,
        'twod10': twod10,
        'd12': d12,
        'd20': d20,
        'total': total,
        'max_roll': max_roll,
        'row_number': row_number
    }
    return render(request, 'dnd_roll_local.html', context)


def dnd_rolls_api(request, roll_size):
    dices = [4, 6, 8, 10, 10, 20]
    length = [roll_size, roll_size, roll_size, roll_size, roll_size, roll_size]
    rolls = []
    if roll_size < 10000:
        dice_request = {
            "jsonrpc": "2.0",
            "method": "generateIntegerSequences",
            "params": {
                "apiKey": "4be61dcd-5df7-423f-a7ae-9864d1e12659",
                "n": 6,
                "length": length,
                "min": [1, 1, 1, 1, 1, 1],
                "max": dices,
                "replacement": True
            },
            "id": 42
        }
        response = requests.post("https://api.random.org/json-rpc/2/invoke", json=dice_request)
        if response.status_code != 200:
            context = {
                'title': 'DND Roller',
                'content': 'roller',
                'rolls': [],
                'max_roll': "Error",
                'row_number': "Error. API is currently occupied, try again tomorrow"
            }
            return render(request, 'dnd_roll.html', context)
        values = response.json()
        values = values["result"]["random"]["data"]
        max_roll = 0
        row_number = 1
        for x in range(0, roll_size):
            total = values[0][x] + values[1][x] + values[2][x] + values[3][x] + values[4][x] + values[5][x]
            rolls.append({
                "d4": values[0][x],
                "d6": values[1][x],
                "d8": values[2][x],
                "oned10": values[3][x],
                "twod10": values[4][x],
                "d20": values[5][x],
                "total": total
            })
            if total > max_roll:
                max_roll = total
                row_number = x + 1
        context = {
            'title': 'DND Roller',
            'content': 'roller',
            'rolls': rolls,
            'max_roll': max_roll,
            'row_number': row_number
        }
        return render(request, 'dnd_roll.html', context)
    context = {
        'title': 'DND Roller',
        'content': 'roller',
        'rolls': [],
        'max_roll': "Error",
        'row_number': "Error. Too many roles requested"
    }
    return render(request, 'dnd_roll.html', context)
