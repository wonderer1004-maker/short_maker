#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/install_font.py
if [ ! -f config.json ]; then cp config.example.json config.json; fi
.venv/bin/python app.py doctor
if [ ! -f output/demo/short.mp4 ]; then .venv/bin/python app.py demo; fi
.venv/bin/python app.py dashboard
