#
# Options
#

PYTHON = python
FILE_WITH_VERSION = src/gtimelog/__init__.py
FILE_WITH_CHANGELOG = CHANGES.rst

#
# Interesting targets
#

manpages = gtimelog.1
po_dir = src/gtimelog/po
po_files = $(wildcard $(po_dir)/*.po)
mo_dir = src/gtimelog/locale
mo_files = $(patsubst $(po_dir)/%.po,$(mo_dir)/%/LC_MESSAGES/gtimelog.mo,$(po_files))
fallback_ui_files = src/gtimelog/gtimelog-gtk3.10.ui src/gtimelog/preferences-gtk3.10.ui
schema_dir = src/gtimelog/data
schema_files = $(schema_dir)/gschemas.compiled
runtime_files = $(schema_files) $(mo_files) $(fallback_ui_files)

.PHONY: all
all: $(manpages) $(runtime_files)

.PHONY: run
run: $(runtime_files)
	./gtimelog

.PHONY: check test
check: test
	desktop-file-validate gtimelog.desktop
	appstream-util validate-relax gtimelog.appdata.xml

test:
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
	git config filter.po.clean 'msgcat - --no-location'
	cd $(po_dir) && intltool-update -g gtimelog -p
	for po in $(po_files); do msgmerge -U $$po $(po_dir)/gtimelog.pot; done

%-gtk3.10.ui: %.ui
	sed -e 's/margin_start/margin_left/' \
	    -e 's/margin_end/margin_right/' \
	    -e '/property name="max_width_chars"/d' \
	    -e '/GtkHeaderBar/,$$ s/<property name="position">.*<\/property>//' \
	    < $< > $@.tmp
	mv $@.tmp $@

$(mo_dir)/%/LC_MESSAGES/gtimelog.mo: $(po_dir)/%.po
	@mkdir -p $(@D)
	msgfmt -o $@ $<

$(schema_files): $(schema_dir)/org.gtimelog.gschema.xml
	glib-compile-schemas $(schema_dir)

.PHONY: clean
clean:
	rm -rf temp tmp build gtimelog.egg-info $(runtime_files) $(mo_dir)
	find -name '*.pyc' -delete

include release.mk

.PHONY: distcheck
distcheck: distcheck-wheel  # add to the list of checks defined in release.mk

.PHONY: distcheck-wheel
distcheck-wheel:
	@pkg_and_version=`$(PYTHON) setup.py --name`-`$(PYTHON) setup.py --version` && \
	  unzip -l dist/$$pkg_and_version-py2.py3-none-any.whl | \
	  grep -q gtimelog.mo && \
	  echo "wheel seems to be ok"

%.1: %.rst
	rst2man $< > $@

%.5: %.rst
	rst2man $< > $@
