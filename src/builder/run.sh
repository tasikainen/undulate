#!/bin/sh
exec gunicorn -b :5001 --timeout 120 --access-logfile - --error-logfile - api:app
