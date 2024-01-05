#!/bin/bash
./setup.sh
./build.sh
gunicorn atilanogarciawebsite.asgi:application -k uvicorn.workers.UvicornWorker --reload
