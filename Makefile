all : test lint todo black

test :
	python3 -m unittest discover -s tests

lint :
	pyflakes *.py */*.py */*/*.py || true

todo :
	egrep 'FIXME|TODO' *.py */*.py */*/*.py

black :
	black --diff ./

coverage :
	coverage run --source=molior,topologist -m unittest discover -s tests
	coverage html
	coverage report

.PHONY : all test lint todo black coverage
