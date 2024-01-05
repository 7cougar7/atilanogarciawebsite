#!/usr/bin/env bash
DIR="./venv"
if [ ! -d "$DIR" ]; then
	python3 -m venv venv
    source venv/bin/activate
    pip3 install -r requirements.txt
    pre-commit install
fi
source venv/bin/activate
