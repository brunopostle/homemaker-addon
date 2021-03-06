all : test lint todo

test :
	python3 -m unittest discover -v -s tests

lint :
	pyflakes *.py */*.py || true

todo :
	egrep 'FIXME|TODO' *.py */*.py

.PHONY : all test lint todo
