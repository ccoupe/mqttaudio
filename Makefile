#
# Makefile for mqttaudio
#
PRJ=mqttaudio
DESTDIR=/usr/local/lib/$(PRJ)
SRCDIR=$(HOME)/Projects/iot/$(PRJ)
LAUNCH=$(PRJ).sh
SERVICE=$(PRJ).service

NODE := $(shell hostname)
SHELL := /bin/bash 

$(HOME)/tb-env:
	sudo apt install -y python3-venv
	python -m venv $(HOME)/sb-env
	( \
	set -e ;\
	source $(HOME)/sb-env/bin/activate; \
	pip install -r $(SRCDIR)/requirements.txt; \
	)

$(DESTDIR):
	sudo mkdir -p ${DESTDIR}
	sudo mkdir -p ${DESTDIR}/lib	
	sudo mkdir -p ${DESTDIR}/chimes	
	sudo cp ${SRCDIR}/chimes/* ${DESTDIR}/chimes
	sudo mkdir -p ${DESTDIR}/sirens
	sudo cp ${SRCDIR}/sirens/* ${DESTDIR}/sirens
	sudo cp ${SRCDIR}/lib/Audio.py ${DESTDIR}/lib
	sudo cp ${SRCDIR}/lib/MqttMycroft.py ${DESTDIR}/lib
	sudo cp ${SRCDIR}/lib/Chatbot.py ${DESTDIR}/lib
	sudo cp ${SRCDIR}/lib/Settings.py ${DESTDIR}/lib
	sudo cp ${SRCDIR}/bridge.py ${DESTDIR}
	sudo cp ${SRCDIR}/Makefile ${DESTDIR}
	sudo cp ${SRCDIR}/pi5.json ${DESTDIR}
	sudo cp ${SRCDIR}/requirements.txt ${DESTDIR}
	sudo cp ${SRCDIR}/mqttaudio.service ${DESTDIR}
	sudo chown -R ${USER} ${DESTDIR}
	sed  s/{NODE}/$(NODE)/ <$(SRCDIR)/$(LAUNCH) >$(DESTDIR)/$(LAUNCH)
	sudo chmod +x ${DESTDIR}/${LAUNCH}
	#sudo cp ${DESTDIR}/${SERVICE} /etc/systemd/system
	#sudo systemctl enable ${SERVICE}
	#sudo systemctl daemon-reload
	#sudo systemctl restart ${SERVICE}
	
install: $(HOME)/tb-env $(DESTDIR)

update: 
	sudo cp ${SRCDIR}/lib/Audio.py ${DESTDIR}/lib
	sudo cp ${SRCDIR}/lib/MqttMycroft.py ${DESTDIR}/lib
	sudo cp ${SRCDIR}/lib/Chatbot.py ${DESTDIR}/lib
	sudo cp ${SRCDIR}/lib/Settings.py ${DESTDIR}/lib
	sudo cp ${SRCDIR}/bridge.py ${DESTDIR}
