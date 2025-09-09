#!/usr/bin/env bash

# Execute the Django command to check and notify reviewers whose due date has passed.
./manage.py check_overdue_reviews
