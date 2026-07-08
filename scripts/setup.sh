#!/bin/bash

set -e

echo " -- Setup Dev Container -- "

pip install --upgrade pip

pip install -r shared/requirements.txt
pip install -r app/requirements.txt
pip install -r worker/requirements.txt

pip install -e shared --no-deps

sudo chown -R vscode:vscode ~/.claude