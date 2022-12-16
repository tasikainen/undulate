#!/bin/bash

# KOSH is assumed to be the public address of the host where the containers are running
KOSH=
# Should be completed with the parameters needed in pyodbc for accessing the Microsoft SQL Server database (or Azure SQL Database)
DATABASE_SERVER=
DATABASE_NAME=
DATABASE_USERNAME=
DATABASE_PASSWORD=

# The values used by the ui component for accessing datapi
# These are copied by the run-nivel-ui.sh script to the startup folder of nivel-ui
GRAPHS_URL=http://$KOSH:5005
API_URL=http://$KOSH:5004

# Address of the log_data_api as seen on KOSH
LOG_DATA_API_HOSTNAME=localhost
LOG_DATA_API_PORT=5000

# For shiny (undulate-app) that is accessing datapi from KOSH
# This value is copied by the run-shiny.sh script to the folder undulate-app folder
DATAPI_URL_ON_HOST=http://localhost:5004/dbquery

# Values neede by builder for accessing the Docker image repository, eg. Docker Hub
REGISTRY_USER_NAME=
REGISTRY_TOKEN=
