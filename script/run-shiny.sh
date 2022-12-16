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

echo "DATAPI_URL_ON_HOST=$DATAPI_URL_ON_HOST" > $projectfolder/src/shiny/undulate-app/env.txt

sudo docker run -d --rm --name "shiny-daemon$postfix" --network="host" \
	--mount type=bind,source=$projectfolder/src/shiny/undulate-app,target=/app/shiny-server/undulate-app \
	--mount type=bind,source=$projectfolder/src/shiny/shiny-server,target=/etc/shiny-server \
	"shiny$postfix"
