#!/bin/bash
sleep 10s
mkdir -p /opendss/logs/
cd /opendss/model
python3 opendssagent.py >/opendss/logs/config.log 2>&1
