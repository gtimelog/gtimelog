Updating Ubuntu PPA
===================

Intended audience: future Marius.

Here's how I uploaded 0.11.2-0mg1 to the PPA:

- ``git remote add --no-tags https://salsa.debian.org/debian/gtimelog.git -``
  (--no-tags because otherwise zest.releaser will push all the debian-specific
  tags to my github when I do regular upstream releases)

- ``git fetch salsa``

- ``git checkout debian/master && git merge --no-ff``

- ``git checkout ppa && git merge debian/master``

- resolved merge conflicts (especially to debian/changelog)

- ``git add -u && git merge --continue``

- ``git checkout debian/master``

- ``gbp import-orig --uscan``

- ``git checkout ppa && git merge debian/master``

- updated debian/changelog

- had to refresh a Quilt patch with ``quilt push -f``, edit src/gtimelog/main.py,
  ``quilt refresh && quilt pop -a``

- tested the build with ``make pbuilder-test-build``

- fixed debian/gtimelog.install

- tested the build with ``make pbuilder-test-build``

- tested the built package with ``sudo dpkg -i ~/pbuilder/xenial_result/gtimelog_0.11.2-0mg1_all.deb``

- ``make upload-to-ppa``

- ``ppa-gtimelog-copy-packages -vw`` and waited

- wrote this document

- ``git push``
