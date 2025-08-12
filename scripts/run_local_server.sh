#!/bin/zsh
echo "Starting local server..."
source ./setup.sh
source ./build.sh
python manage.py runserver
