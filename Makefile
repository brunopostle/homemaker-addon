test :
	python3 -m unittest  discover -v -s tests

lint :
	pyflakes *.py */*.py || true

.PHONY : test
