#!/bin/bash
if [ ! -z "$1" ] 
then
	postfix="-$1"
else
	postfix=""
fi

sudo docker stop "builder-daemon$postfix"
sudo docker stop "cluster_control-daemon$postfix"
sudo docker stop "shiny-daemon$postfix"
sudo docker stop "simulient-daemon$postfix"

./run-builder.sh $1
./run-cluster_control.sh $1
./run-shiny.sh $1
./run-simulient.sh $1

