#
# Options
#

PYTHON = python
FILE_WITH_VERSION = src/gtimelog/__init__.py
FILE_WITH_CHANGELOG = NEWS.rst

#
# Interesting targets
#

manpages = gtimelog.1 gtimelogrc.5
po_files = $(wildcard po/*.po)
mo_files = $(patsubst po/%.po,locale/%/LC_MESSAGES/gtimelog.mo,$(po_files))

.PHONY: all
all: $(manpages) $(mo_files) gschemas.compiled src/gtimelog/experiment-gtk3.10.ui

.PHONY: run
run: gschemas.compiled $(mo_files)
	./mockup.py

.PHONY: check test
check test:
	./runtests

.PHONY: coverage
coverage:
	detox -e coverage,coverage3 -- -p
	coverage combine
	coverage report

.PHONY: coverage-diff
coverage-diff: coverage
	coverage xml
	diff-cover coverage.xml

.PHONY: update-translations
update-translations:
	cd po && intltool-update -g gtimelog -p
	for po in $(po_files); do msgmerge -U $$po po/gtimelog.pot; done

%-gtk3.10.ui: %.ui
	sed -e 's/margin_start/margin_left/' -e 's/margin_end/margin_right/' < $< > $@.tmp
	mv $@.tmp $@

locale/%/LC_MESSAGES/gtimelog.mo: po/%.po
	mkdir -p $(@D)
	msgfmt -o $@ $<

gschemas.compiled: org.gtimelog.gschema.xml
	glib-compile-schemas .

.PHONY: clean
clean:
	rm -rf temp tmp build gtimelog.egg-info
	find -name '*.pyc' -delete

.PHONY: dist
dist:
	$(PYTHON) setup.py sdist

.PHONY: distcheck
distcheck: check dist
	# Bit of a chicken-and-egg here, but if the tree is unclean, make
	# distcheck will fail.
	@test -z "`git status -s 2>&1`" || { echo; echo "Your working tree is not clean" 1>&2; git status; exit 1; }
	make dist
	pkg_and_version=`$(PYTHON) setup.py --name`-`$(PYTHON) setup.py --version` && \
	rm -rf tmp && \
	mkdir tmp && \
	git archive --format=tar --prefix=tmp/tree/ HEAD | tar -xf - && \
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

.PHONY: releasechecklist
releasechecklist:
	@$(PYTHON) setup.py --version | grep -qv dev || { \
	    echo "Please remove the 'dev' suffix from the version number in $(FILE_WITH_VERSION)"; exit 1; }
	@$(PYTHON) setup.py --long-description | rst2html --exit-status=2 > /dev/null
	@ver_and_date="`$(PYTHON) setup.py --version` (`date +%Y-%m-%d`)" && \
	    grep -q "^$$ver_and_date$$" NEWS.rst || { \
	        echo "$(FILE_WITH_CHANGELOG) has no entry for $$ver_and_date"; exit 1; }
	make distcheck

.PHONY: release
release: releasechecklist
	# I'm chicken so I won't actually do these things yet
	@echo "Please run"
	@echo
	@echo "  rm -rf dist && $(PYTHON) setup.py sdist && twine upload dist/* && git tag `$(PYTHON) setup.py --version`"
	@echo
	@echo "Please increment the version number in $(FILE_WITH_VERSION)"
	@echo "and add a new empty entry at the top of $(FILE_WITH_CHANGELOG), then"
	@echo
	@echo '  git commit -a -m "Post-release version bump" && git push && git push --tags'
	@echo


%.1: %.rst
	rst2man $< > $@

%.5: %.rst
	rst2man $< > $@
