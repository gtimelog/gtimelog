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


# Debian packaging
TARGET_DISTRO := xenial
source := gtimelog
version := $(shell dpkg-parsechangelog | awk '$$1 == "Version:" { print $$2 }')
upstream_version := $(shell python setup.py --version)

.PHONY: clean-source-tree
clean-source-tree:
	rm -rf pkgbuild
	mkdir pkgbuild
	cd pkgbuild && pip download --no-deps --no-binary :all: $(source)==$(upstream_version)
	cd pkgbuild && tar xf $(source)-$(upstream_version).tar.gz
	cd pkgbuild && mv $(source)-$(upstream_version) $(source)
	cd pkgbuild && mv $(source)-$(upstream_version).tar.gz $(source)_$(upstream_version).orig.tar.gz
	git archive --format=tar --prefix=pkgbuild/$(source)/ HEAD debian/ | tar -xf -

.PHONY: source-package
source-package pkgbuild/$(source)_$(version)_source.changes: clean-source-tree
	cd pkgbuild/$(source) && dch -r -D $(TARGET_DISTRO) "" && debuild -S -i -k$(GPGKEY)
	rm -rf pkgbuild/$(source)
	@echo
	@echo "Built pkgbuild/$(source)_$(version)_source.changes"

.PHONY: binary-package
binary-package: clean-source-tree
	cd pkgbuild/$(source) && dch -r -D $(TARGET_DISTRO) "" && debuild -i -k$(GPGKEY)
	rm -rf pkgbuild/$(source)
	@echo
	@echo "Built pkgbuild/$(source)_$(version)_all.deb"

.PHONY: pbuilder-test-build
pbuilder-test-build: pkgbuild/$(source)_$(version)_source.changes
	# NB: you need to periodically run pbuilder-dist $(TARGET_DISTRO) update
	pbuilder-dist $(TARGET_DISTRO) build pkgbuild/$(source)_$(version).dsc
	@echo
	@echo "Built ~/pbuilder/$(TARGET_DISTRO)_result/$(source)_$(version)_all.deb"

.PHONY: upload-to-ppa
upload-to-ppa: pkgbuild/$(source)_$(version)_source.changes
	dput ppa:gtimelog-dev/ppa pkgbuild/$(source)_$(version)_source.changes
