#!/bin/zsh
# Activate virtual environment if it exists
if [ -d "../venv" ]; then
    source ../venv/bin/activate
fi

pip install -r ../requirements.txt
python ./setup_fontawesome.py
python ../manage.py migrate
python ../manage.py collectstatic --noinput --clear
