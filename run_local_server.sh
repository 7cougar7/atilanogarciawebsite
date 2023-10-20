#!/bin/bash
DIR="./venv"
if [ ! -d "$DIR" ]; then
	python3 -m venv venv
fi
source venv/bin/activate
./build.sh
./start_server.sh
