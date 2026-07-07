#!/bin/bash

set -e

echo " -- Setup Dev Container -- "

pip install --upgrade pip

pip install -r shared/requirements.txt
pip install -r app/requirements.txt
pip install -r apscheduler/requirements.txt

pip install -e shared --no-deps