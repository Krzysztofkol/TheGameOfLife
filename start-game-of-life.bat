@echo off
::move to the current folder
cd /d "%~dp0"
::install or update dependencies
::python -m pip install -U pip
::pip install flask
::pip install flask_cors
::pip install pandas
::run frontend first
start "" "game-of-life-frontend.html"
::run backend
python game-of-life-backend.py