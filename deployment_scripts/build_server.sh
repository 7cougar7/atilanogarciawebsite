#!/usr/bin/env bash
pip install -r requirements.txt
python scripts/setup_fontawesome.py
python manage.py migrate
python manage.py collectstatic --noinput --clear
