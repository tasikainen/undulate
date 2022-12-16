#!/bin/bash
projectfolder=`dirname $PWD`
topfolder=`dirname $projectfolder`
source ../../config/setenv.sh

if [ ! -z "$1" ]
then
        postfix="-$1"
else
        postfix=""
fi

sudo docker run -v /run/docker.sock:/var/run/docker.sock \
    --env REGISTRY_TOKEN=$REGISTRY_TOKEN \
    --env LOG_DATA_API_HOSTNAME=$LOG_DATA_API_HOSTNAME \
    --env SERVICES_DOMAIN= \
    --env LOG_DATA_API_PORT=$LOG_DATA_API_PORT \
    --env APPLICATION=builder \
    --net host --rm  \
    -d --name "builder-daemon$postfix" \
    "builder$postfix"
