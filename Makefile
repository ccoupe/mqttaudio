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

.PHONY: all update install clean realclean setup_dir stop start
all: install

PYTOPF := ${DESTDIR}/main.py ${DESTDIR}/gvars.py ${DESTDIR}/speechio.py
PYLIBF := ${DESTDIR}/lib/Audio.py ${DESTDIR}/lib/Constants.py \
	${DESTDIR}/lib/Chatbot.py ${DESTDIR}/lib/Settings.py
MFILES := ${DESTDIR}/${NODE}.toml ${DESTDIR}/Makefile ${DESTDIR}/${SERVICE} \
	${DESTDIR}/${LAUNCH}
PROMPTS := ${DESTDIR}/prompts/pi5-deepseek.prompt

${DESTDIR}/main.py : ${SRCDIR}/main.py
	cp ${SRCDIR}/main.py ${DESTDIR}/main.py
	
${DESTDIR}/gvars.py : ${SRCDIR}/gvars.py
	cp ${SRCDIR}/gvars.py ${DESTDIR}/gvars.py
	
${DESTDIR}/speechio.py : ${SRCDIR}/speechio.py
	cp ${SRCDIR}/speechio.py ${DESTDIR}/speechio.py
	
${DESTDIR}/lib/Audio.py : ${SRCDIR}/lib/Audio.py
	cp ${SRCDIR}/lib/Audio.py ${DESTDIR}/lib/Audio.py
	
${DESTDIR}/lib/Constants.py : ${SRCDIR}/lib/Constants.py
	cp ${SRCDIR}/lib/Constants.py ${DESTDIR}/lib/Constants.py
	
${DESTDIR}/lib/Chatbot.py : ${SRCDIR}/lib/Chatbot.py
	cp ${SRCDIR}/lib/Chatbot.py ${DESTDIR}/lib/Chatbot.py
	
${DESTDIR}/lib/Settings.py:  ${SRCDIR}/lib/Settings.py
	cp ${SRCDIR}/lib/Settings.py ${DESTDIR}/lib/Settings.py
	
${DESTDIR}/prompts/pi5-deepseek.prompt: ${SRCDIR}/prompts/pi5-deepseek.prompt
	cp ${SRCDIR}/prompts/pi5-deepseek.prompt ${DESTDIR}/prompts
	
${DESTDIR}/${LAUNCH}: ${SRCDIR}/launch.sh
	sed  s!PYENV!${PYENV}! <${SRCDIR}/launch.sh >$(DESTDIR)/$(LAUNCH)

${PYENV}: ${SRCDIR}/requirements.txt
	sudo mkdir -p ${PYENV}
	sudo chown ${USER} ${PYENV}
	python3 -m venv ${PYENV}
	( \
	set -e ;\
	source ${PYENV}/bin/activate; \
	pip install -r $(SRCDIR)/requirements.txt; \
	)

start:
	systemctl --user daemon-reload
	systemctl --user enable ${SERVICE}
	systemctl --user restart ${SERVICE}

stop:
	systemctl --user stop ${SERVICE}
	systemctl --user disable ${SERVICE}
	
${DESTDIR}: 
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
		
update: ${PYTOPF} ${PYLIBF} ${MFILES} ${PROMPTS}
	sudo chown -R ${USER} ${DESTDIR}


install: ${DESTDIR} ${PYENV} update

lint:
	 flake8 --indent-size 2 --max-line-length 90 --ignore=W293,F824 \
--exclude .venv,${PYENV}
	 
clean: 
	systemctl --user stop ${SERVICE}
	systemctl --user disable ${SERVICE}
	sudo rm -f /etc/xdg/systemd/user/${SERVICE}
	sudo rm -rf ${DESTDIR}

realclean: clean
	rm -rf ${PYENV}

