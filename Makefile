#
# Options
#

PYTHON = python3
FILE_WITH_VERSION = src/gtimelog/__init__.py
FILE_WITH_CHANGELOG = CHANGES.rst

# Let's use the tox-installed coverage because we'll be sure it's there and has
# the necessary plugins.
COVERAGE = .tox/coverage/bin/coverage

#
# Interesting targets
#

manpages = gtimelog.1
po_dir = src/gtimelog/po
po_files = $(wildcard $(po_dir)/*.po)
mo_dir = src/gtimelog/locale
mo_files = $(patsubst $(po_dir)/%.po,$(mo_dir)/%/LC_MESSAGES/gtimelog.mo,$(po_files))
schema_dir = src/gtimelog/data
schema_files = $(schema_dir)/gschemas.compiled
runtime_files = $(schema_files) $(mo_files)

.PHONY: all
all: $(manpages) $(runtime_files)       ##: build everything

.PHONY: run
run: $(runtime_files)                   ##: run directly from the source tree
	./gtimelog

.PHONY: test
test:                                   ##: run tests
	tox -p auto

.PHONY: check
check: check-desktop-file check-appstream-metadata ##: run tests and additional checks

.PHONY: check
check-desktop-file:                     ##: validate desktop file
	desktop-file-validate gtimelog.desktop

.PHONY: check
check-appstream-metadata:               ##: validate appstream metadata file
	appstreamcli validate --strict --explain --pedantic gtimelog.appdata.xml


.PHONY: coverage
coverage:                               ##: measure test coverage
	tox -e coverage

.PHONY: coverage-diff
coverage-diff: coverage                 ##: find untested code in this branch
	$(COVERAGE) xml
	diff-cover coverage.xml

.PHONY: flake8
flake8:                                 ##: check for style problems
	tox -e flake8

.PHONY: isort
isort:                                  ##: check for badly sorted improts
	tox -e isort

.PHONY: update-translations
update-translations:                    ##: extract new translatable strings from source code and ui files
	git config filter.po.clean 'msgcat - --no-location'
	cd $(po_dir) && intltool-update -g gtimelog -p
	for po in $(po_files); do msgmerge -U $$po $(po_dir)/gtimelog.pot; done

.PHONY: mo-files
mo-files: $(mo_files)

.PHONY: flatpak
flatpak:                                ##: build a flatpak package
	# you may need to install the platform and sdk before this will work
	# flatpak install flathub org.gnome.Platform//3.82 org.gnome.Sdk//3.38
	# note that this builds the code from git master, not your local working tree!
	flatpak-builder --force-clean build/flatpak flatpak/org.gtimelog.GTimeLog.yaml
	# to run it do
	# flatpak-builder --run build/flatpak flatpak/org.gtimelog.GTimeLog.yaml gtimelog

.PHONY: flatpak-install
flatpak-install:                        ##: build and install a flatpak package
	# you may need to install the platform and sdk before this will work
	# flatpak install flathub org.gnome.Platform//3.38 org.gnome.Sdk//3.38
	# note that this builds the code from git master, not your local working tree!
	flatpak-builder --force-clean build/flatpak flatpak/org.gtimelog.GTimeLog.yaml --install --user
	# to run it do
	# flatpak run org.gtimelog.GTimeLog

$(mo_dir)/%/LC_MESSAGES/gtimelog.mo: $(po_dir)/%.po
	@mkdir -p $(@D)
	msgfmt -o $@ $<

$(schema_files): $(schema_dir)/org.gtimelog.gschema.xml
	glib-compile-schemas $(schema_dir)

.PHONY: clean
clean:                                  ##: clean build artifacts
	rm -rf temp tmp build gtimelog.egg-info $(runtime_files) $(mo_dir)
	find -name '*.pyc' -delete

include release.mk

.PHONY: distcheck
distcheck: distcheck-wheel    # add to the list of checks defined in release.mk
distcheck: distcheck-appdata  # add to the list of checks defined in release.mk

.PHONY: distcheck-wheel
distcheck-wheel:
	@pkg_and_version=`$(PYTHON) setup.py --name`-`$(PYTHON) setup.py --version` && \
	  unzip -l dist/$$pkg_and_version-py2.py3-none-any.whl | \
	  grep -q gtimelog.mo && \
	  echo "wheel seems to be ok"

APPDATA_FILE = gtimelog.appdata.xml
APPDATA_FORMAT = "<release version="'"'$(changelog_ver)'"'" date="'"'"$(changelog_date)"'"'" />"

.PHONY: distcheck-appdata
distcheck-appdata:
	@ver_and_date=$(APPDATA_FORMAT) && \
	    grep -q "^$$ver_and_date$$" $(APPDATA_FILE) || { \
	        echo "$(APPDATA_FILE) has no entry for $$ver_and_date"; exit 1; }

%.1: %.rst
	rst2man $< > $@

%.5: %.rst
	rst2man $< > $@

.PHONY: update-github-branch-protection-rules
update-github-branch-protection-rules:  ##: update GitHub branch protection rules
	gh api -X PUT -H "Accept: application/vnd.github+json" \
		-H "X-GitHub-Api-Version: 2022-11-28" \
		/repos/{owner}/{repo}/branches/master/protection/required_status_checks/contexts \
		-f "contexts[]=check-manifest"                         \
		-f "contexts[]=check-python-versions"                  \
		-f "contexts[]=flake8"                                 \
		-f "contexts[]=isort"                                  \
		-f "contexts[]=Python 3.7"                             \
		-f "contexts[]=Python 3.8"                             \
		-f "contexts[]=Python 3.9"                             \
		-f "contexts[]=Python 3.10"                            \
		-f "contexts[]=Python 3.11"                            \
		-f "contexts[]=Python 3.12"                            \
		-f "contexts[]=Python 3.13"                            \
		-f "contexts[]=Python pypy3.10"                        \
		-f "contexts[]=continuous-integration/appveyor/branch" \
		-f "contexts[]=continuous-integration/appveyor/pr"
