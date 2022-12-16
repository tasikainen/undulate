#!/bin/bash
if [ ! -z "$1" ] 
then
	postfix="-$1"
else
	postfix=""
fi

sudo docker build ../src/builder/ -t "builder$postfix"
sudo docker build ../src/cluster_control/ -t "cluster_control$postfix"
sudo docker build ../src/shiny/ -t "shiny$postfix"
sudo docker build ../src/simulient/ -t "simulient$postfix"
