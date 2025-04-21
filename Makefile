SHELL=/bin/bash

all : lint test todo black

test :
	pytest tests/

lint :
	pyflakes *.py {tests,topologist,molior}/*.py {topologist,molior}/*/*.py || true

todo :
	grep -E 'FIXME|TODO' *.py {tests,topologist,molior}/*.py {topologist,molior}/*/*.py || true

black :
	black --diff *.py {tests,topologist,molior}/

coverage :
	coverage run --source=molior,topologist -m unittest discover -s tests
	coverage html
	coverage report

.PHONY : all test lint todo black coverage
