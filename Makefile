# Copyright (C) 2013-2014 Craig Phillips.  All rights reserved.
#
# GSync top level makefile.

all:
	@echo "Run make with the following targets:"
	@echo "    install        Install the GSync application in this system"
	@echo "    uninstall      Remove the GSync application from this system"
	@echo "    runtests       Run Gsync unit and regression tests"
	@echo "    ctags          Generate ctags file"

ifneq (0,$(shell id -u))
SUDO:= sudo
else
SUDO:=
endif

reverse = $(if $(1),$(call reverse,\
	$(wordlist 2,$(words $(1)),$(1)))) $(firstword $(1)\
)
reverse = $(shell printf "%s\n" $(strip $1) | tac)

SRC_FILES:= $(shell find bin/ libgsync/ -type f)
TEST_FILES:= $(shell find tests/ -type f -name "*.py")

PYLINT:= $(shell which pylint)
ifneq (,$(PYLINT))
PYLINT_TARGETS:= $(addprefix pylint/,$(SRC_FILES))
PYLINT_TEST_TARGETS:= $(addprefix pylint/,$(TEST_FILES))
else
PYLINT_TARGETS:=
PYLINT_TEST_TARGETS:=
endif
.PHONY: $(PYLINT_TARGETS) $(PYLINT_TEST_TARGETS)

MANIFEST:= $(if $(wildcard MANIFEST),$(shell cat MANIFEST),)
RM_MANIFEST:= $(addprefix uninstall_,\
	$(filter-out \
		%/bin/ \
		%/dist-packages/ \
		,$(wildcard $(MANIFEST) $(call reverse,$(sort $(dir $(MANIFEST))))),\
	)\
)

.PHONY: $(RM_MANIFEST)

$(RM_MANIFEST): uninstall_% : %
	@[ -e "$<" ] || { \
	    echo >&2 "Error: GSync is not installed" ; \
		exit 1 ; \
	}
	@[ $(shell id -u) -eq 0 ] || { \
		echo >&2 "Error: You must be root" ; \
		exit 1 ; \
	}
	@if [ -d $< ] ; then \
		rmdir -v $< ; \
	else \
		rm -vf $< ; \
	fi

clean:
	@rm -rf \
		build/ dist/ gsync.egg-info/ htmlcov/ \
		regression/output/ regression/tmp/
	@find . -name \*.pyc -delete

check: $(PYLINT_TARGETS)
check_unittests: $(PYLINT_TEST_TARGETS)

.pylintrc:
	@pylint --generate-rcfile >$@

$(PYLINT_TARGETS): pylint/% : % | .pylintrc
	@echo Checking $<
	@pylint -r n --rcfile .pylintrc $<

$(PYLINT_TEST_TARGETS): pylint/% : % | .pylintrc
	@echo Checking $<
	@pylint -E -r n --rcfile .pylintrc $<

uninstall: $(RM_MANIFEST)
	@echo "Uninstall complete"

ctags: $(SRC_FILES)
	@rm -f $@
	@ctags -R -f $@ bin/ libgsync/

install: /usr/local/bin/gsync

bdist build: setup.py $(SRC_FILES)
	@./setup.py $@

/usr/local/bin/gsync: build bdist
	@$(SUDO) ./setup.py install --record MANIFEST
	@$(SUDO) find /usr/local/lib/python2.7/dist-packages/ \
		! -perm -o=r -exec chmod o+r {} \;

PY_COVERAGE:=$(if $(COVERAGE),$(shell which coverage),)

run_unittests:
ifneq (,$(PY_COVERAGE))
	@rm -rf htmlcov/
	@$(PY_COVERAGE) erase
	@$(PY_COVERAGE) run ./setup.py test
	@$(PY_COVERAGE) html --include="libgsync/*"
else
	@./setup.py test
endif

run_regression:
	@./regression/run.sh --verbose-no-tty
