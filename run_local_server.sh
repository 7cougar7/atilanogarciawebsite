#!/bin/zsh
source ./setup.sh
source ./build.sh
gunicorn atilanogarciawebsite.asgi:application -k uvicorn.workers.UvicornWorker --reload
