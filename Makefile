__VERSION__ = "0.9.5"

lint:
	isort custom_components
	black custom_components
	flake8 custom_components

bump:
	bump2version --allow-dirty --current-version $(__VERSION__) patch Makefile custom_components/sjofartsverket/manifest.json

install_dev:
	pip install -r requirements-dev.txt
