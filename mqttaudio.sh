#!/usr/bin/env bash
#sudo killall bluealsa
source ~/tb-env/bin/activate
cd /usr/local/lib/mqttaudio
node=`hostname`
python3 bridge.py -s -c ${node}.json 
