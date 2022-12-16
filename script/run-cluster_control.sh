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

sudo docker run \
    --env LOG_DATA_API_HOSTNAME=$LOG_DATA_API_HOSTNAME \
    --env SERVICES_DOMAIN= \
    --env LOG_DATA_API_PORT=$LOG_DATA_API_PORT \
    --env APPLICATION=cluster_control \
    -v $topfolder/config/k8s-cc5-default-conf:/app/k8s-cc5-default-conf \
    -d --rm --name "cluster_control-daemon$postfix" --network="host" \
    "cluster_control$postfix"
