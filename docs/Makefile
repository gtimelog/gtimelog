.PHONY: build
build:
	rm -rf build && mkdir build
	rst2html --stylesheet mg.css --link-stylesheet website.rst build/index.html
	rst2html --stylesheet mg.css --link-stylesheet index.rst build/docs.html
	rst2html --stylesheet mg.css --link-stylesheet formats.rst build/formats.html
	cp gtimelog.png build/gtimelog.png
	cp mg.css build/mg.css

.PHONY: preview
preview:
	# pip install restview
	restview --css mg.css website.rst
