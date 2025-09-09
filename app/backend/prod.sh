#!/usr/bin/env bash
set -eu

./manage.py migrate
./manage.py runserver 0.0.0.0:8000