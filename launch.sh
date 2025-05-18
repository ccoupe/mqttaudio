#!/usr/bin/env bash
source PYENV/bin/activate
nm-online
cd /usr/local/lib/mqttaudio/
node=`hostname`
python3 main.py -s -c ${node}.toml
