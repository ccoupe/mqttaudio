#!/usr/bin/env bash
#sudo killall bluealsa
source /home/ccoupe/tb-env
cd /usr/local/lib/mqttaudio
python3 bridge.py -s -c {NODE} 
