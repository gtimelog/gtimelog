#
# Options
#

PYTHON = python

#
# Interesting targets
#

.PHONY: all
all:
	@echo "There's nothing that needs building.  Just run ./gtimelog"

.PHONY: check test
check test:
	./runtests

.PHONY: clean
clean:
	rm -rf temp tmp build gtimelog.egg-info
	find -name '*.pyc' -delete

.PHONY: dist
dist:
	$(PYTHON) setup.py sdist

.PHONY: distcheck
distcheck: check dist
	pkg_and_version=`$(PYTHON) setup.py --name`-`$(PYTHON) setup.py --version` && \
	rm -rf tmp && \
	mkdir tmp && \
	bzr export tmp/tree && \
	cd tmp && \
	tar xvzf ../dist/$$pkg_and_version.tar.gz && \
	diff -ur $$pkg_and_version tree -x PKG-INFO -x setup.cfg -x '*.egg-info' && \
	cd $$pkg_and_version && \
	make dist check && \
	cd .. && \
	mkdir one two && \
	cd one && \
	tar xvzf ../../dist/$$pkg_and_version.tar.gz && \
	cd ../two/ && \
	tar xvzf ../$$pkg_and_version/dist/$$pkg_and_version.tar.gz && \
	cd .. && \
	diff -ur one two -x SOURCES.txt && \
	cd .. && \
	rm -rf tmp && \
	echo "sdist seems to be ok"
# I'm ignoring SOURCES.txt since it appears that the second sdist gets a new
# source file, namely, setup.cfg.  Setuptools/distutils black magic, may it rot
# in hell forever.

.PHONY: releasechecklist
releasechecklist:
	@$(PYTHON) setup.py --version | grep -qv dev || { \
	    echo "Please remove the 'dev' suffix from the version number in src/gtimelog/__init__.py"; exit 1; }
	@$(PYTHON) setup.py --long-description | rst2html --exit-status=2 > /dev/null
	@ver_and_date="`$(PYTHON) setup.py --version` (`date +%Y-%m-%d`)" && \
	    grep -q "^$$ver_and_date$$" NEWS.txt || { \
	        echo "NEWS.txt has no entry for $$ver_and_date"; exit 1; }
	# Bit of a chicken-and-egg here, but if the tree is unclean, make
	# distcheck will fail.  Thankfully bzr lets me uncommit.
	@test -z "`bzr status 2>&1`" || { echo; echo "Your working tree is not clean" 1>&2; bzr status; exit 1; }
	make distcheck

.PHONY: release
release: releasechecklist
	# I'm chicken so I won't actually do these things yet
	@echo "Please run"
	@echo
	@echo "  $(PYTHON) setup.py sdist register upload && bzr tag `$(PYTHON) setup.py --version`"
	@echo
	@echo "Please increment the version number in src/gtimelog/__init__.py"
	@echo "and add a new empty entry at the top of NEWS.txt, then"
	@echo
	@echo '  bzr ci -m "Post-release version bump" && bzr push'
	@echo

