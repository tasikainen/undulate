#!/bin/sh
exec gunicorn -b :5006 --timeout 120 --access-logfile - --error-logfile - api:app
