all : test lint

test :
	python3 -m unittest discover -v -s tests

lint :
	pyflakes *.py */*.py || true

.PHONY : all test lint
