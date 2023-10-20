#!/bin/bash
DIR="./venv"
if [ ! -d "$DIR" ]; then
	python3 -m venv venv
fi
source venv/bin/activate
./build.sh
gunicorn atilanogarciawebsite.asgi:application -k uvicorn.workers.UvicornWorker
