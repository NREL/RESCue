#!/bin/bash

systemctl stop nodered
systemctl stop ot-sim
killall node
cd /root/.node-red/
npm install -g --offline node-red-contrib-ot-sim-0.0.1.tgz
systemctl start nodered
systemctl start ot-sim
