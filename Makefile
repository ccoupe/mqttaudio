#
# Makefile for mqttaudio
#
PRJ ?= mqttaudio
DESTDIR ?= /usr/local/lib/${PRJ}
SRCDIR ?= $(HOME)/Projects/iot/${PRJ}
LAUNCH ?= ${PRJ}.sh
SERVICE ?= $(PRJ).service
PYENV ?= ${DESTDIR}/ma-env

NODE := $(shell hostname)
SHELL := /bin/bash 

${PYENV}:
	sudo mkdir -p ${PYENV}
	sudo chown ${USER} ${PYENV}
	python3 -m venv ${PYENV}
	( \
	set -e ;\
	source ${PYENV}/bin/activate; \
	pip install -r $(SRCDIR)/requirements.txt; \
	)

setup_launch:
	systemctl --user daemon-reload
	systemctl --user enable ${SERVICE}
	systemctl --user restart ${SERVICE}
	
setup_dir:
	sudo mkdir -p ${DESTDIR}
	sudo mkdir -p ${DESTDIR}/lib	
	sudo mkdir -p ${DESTDIR}/chimes
	sudo mkdir -p ${DESTDIR}/sirens
	sudo mkdir -p ${DESTDIR}/prompts
	sudo cp ${SRCDIR}/Makefile ${DESTDIR}
	sudo cp ${SRCDIR}/${NODE}.toml ${DESTDIR}
	sudo cp ${SRCDIR}/requirements.txt ${DESTDIR}
	sudo cp ${SRCDIR}/${SERVICE} ${DESTDIR}
	sudo cp ${SRCDIR}/prompts/* ${DESTDIR}/prompts
	sudo chown -R ${USER} ${DESTDIR}
	sed  s!PYENV!${PYENV}! <${SRCDIR}/launch.sh >$(DESTDIR)/$(LAUNCH)
	sudo chmod +x ${DESTDIR}/${LAUNCH}
	sudo cp ${DESTDIR}/${SERVICE} /etc/xdg/systemd/user
	

#sudo cp ${SRCDIR}/lib/Constants.py ${DESTDIR}/lib
#sudo cp ${SRCDIR}/lib/MqttMycroft.py ${DESTDIR}/lib
#sudo cp ${SRCDIR}/lib/Chatbot.py ${DESTDIR}/lib
#sudo cp ${SRCDIR}/lib/Settings.py ${DESTDIR}/lib
#sudo cp ${SRCDIR}/bridge.py ${DESTDIR}
#sudo cp ${SRCDIR}/gvars.py ${DESTDIR}
#sudo cp ${SRCDIR}/speechio.py ${DESTDIR}
	
update: 
	sudo cp ${SRCDIR}/lib/*.py ${DESTDIR}/lib
	sudo cp ${SRCDIR}/*.py ${DESTDIR}
	sudo cp ${SRCDIR}/${SERVICE} ${DESTDIR}
	#sudo cp ${SRCDIR}/${NODE}.json ${DESTDIR}
	sudo cp ${SRCDIR}/Makefile ${DESTDIR}
	sudo cp ${SRCDIR}/prompts/* ${DESTDIR}/prompts
	sudo cp ${SRCDIR}/${NODE}.toml ${DESTDIR}
	sudo chown -R ${USER} ${DESTDIR}


install: ${PYENV} setup_dir update setup_launch

clean: 
	systemctl --user stop ${SERVICE}
	systemctl --user disable ${SERVICE}
	sudo rm -f /etc/xdg/systemd/user/${SERVICE}
	sudo rm -rf ${DESTDIR}

realclean: clean
	rm -rf ${PYENV}
