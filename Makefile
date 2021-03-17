all : test lint todo black

test :
	python3 -m unittest discover -v -s tests

lint :
	pyflakes *.py */*.py || true

todo :
	egrep 'FIXME|TODO' *.py */*.py

black :
	black --diff ./

.PHONY : all test lint todo black
