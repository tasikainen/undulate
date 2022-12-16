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
	-d --rm --name simulient-daemon --network="host" \
	--env LOG_DATA_API_HOSTNAME=$LOG_DATA_API_HOSTNAME \
	--env SERVICES_DOMAIN= \
	--env LOG_DATA_API_PORT=$LOG_DATA_API_PORT \
	"simulient$postfix"
