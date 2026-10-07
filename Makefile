#
# Makefile for mqttaudio
#

PRJ ?= mqttaudio
DESTDIR ?= /usr/local/lib/${PRJ}
SRCDIR ?= $(HOME)/Projects/iot/${PRJ}
LAUNCH ?= ${PRJ}.sh
SERVICE ?= $(PRJ).service
PYENV ?= ${DESTDIR}/.venv
NODE := $(shell hostname)
SHELL := /bin/bash 
PYFILES = $(shell cd $(SRCDIR); ls *.py)
PYVER ?= 3.11.12

.PHONY: all update install clean distclean setup_dir stop start
all: install

# Define function; $(1) is the python file name.
define copyheader =
$(DESTDIR)/$(1): $(SRCDIR)/$(1)
	cp -u $$^ $$@
endef

# Use function to create recipes for each python file.
$(foreach file,$(PYFILES),$(eval $(call copyheader,$(file))))

# Depend on all destination python files.
pyfiles: $(addprefix $(DESTDIR)/,$(PYFILES))

MFILES := ${DESTDIR}/${NODE}.toml ${DESTDIR}/Makefile ${DESTDIR}/${SERVICE} \
	${DESTDIR}/${LAUNCH}

$(DESTDIR)/$(NODE).toml: $(SRCDIR)/$(NODE).toml
	cp -u $(SRCDIR)/$(NODE).toml $(DESTDIR)

$(DESTDIR)/$(SERVICE):
	cp -u $(SRCDIR)/$(SERVICE) $(DESTDIR)

$(DESTDIR)/Makefile:
	cp -u $(SRCDIR)/Makefile $(DESTDIR)

$(DESTDIR)/$(LAUNCH): $(SRCDIR)/launch.sh
	sed  s!PYENV!${PYENV}! <${SRCDIR}/launch.sh >$(DESTDIR)/$(LAUNCH)

${DESTDIR}/prompts/$(NODE)-deepseek.prompt: 
	mkdir -p $(DESTDIR)/prompts
	cp -u deepseek.prompt $(DESTDIR)/prompts/$(NODE)-deepseek.prompt

${PYENV}: ${SRCDIR}/requirements.txt
	sudo mkdir -p ${PYENV}
	sudo chown ${USER} ${PYENV}
	uv venv --no-project ${PYENV}
	( \
	set -e ;\
	source ${PYENV}/bin/activate ; \
	uv pip install -r $(SRCDIR)/requirements.txt ; \
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
	sudo mkdir -p ${DESTDIR}/chimes
	sudo mkdir -p ${DESTDIR}/sirens
	sudo mkdir -p ${DESTDIR}/prompts
	sudo cp ${SRCDIR}/Makefile ${DESTDIR}
	sudo cp ${SRCDIR}/${NODE}.toml ${DESTDIR}
	sudo cp ${SRCDIR}/requirements.txt ${DESTDIR}
	sudo cp ${SRCDIR}/${SERVICE} ${DESTDIR}
	sudo cp ${SRCDIR}/deepseek.prompt ${DESTDIR}/prompts
	sudo chown -R ${USER} ${DESTDIR}
	sed  s!PYENV!${PYENV}! <${SRCDIR}/launch.sh >$(DESTDIR)/$(LAUNCH)
	sudo chmod +x ${DESTDIR}/${LAUNCH}
	sudo cp ${DESTDIR}/${SERVICE} /etc/xdg/systemd/user
		
update: pyfiles ${MFILES} ${DESTDIR}/prompts/${NODE}-deepseek.prompt
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

distclean: clean
	rm -rf ${PYENV}
