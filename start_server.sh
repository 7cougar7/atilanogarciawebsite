#!/bin/bash
gunicorn atilanogarciawebsite.asgi:application -k uvicorn.workers.UvicornWorker