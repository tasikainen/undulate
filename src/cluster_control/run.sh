#!/bin/sh
export KUBECONFIG='k8s-cc5-default-conf'
exec gunicorn -b :5002 --access-logfile - --error-logfile - api:app
