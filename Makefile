all : test lint todo black

test :
	python3 -m unittest discover -s tests

lint :
	pyflakes *.py {tests,topologist,molior}/*.py {topologist,molior}/*/*.py || true

todo :
	egrep 'FIXME|TODO' *.py {tests,topologist,molior}/*.py {topologist,molior}/*/*.py || true

black :
	black --diff *.py {tests,topologist,molior}/

coverage :
	coverage run --source=molior,topologist -m unittest discover -s tests
	coverage html
	coverage report

.PHONY : all test lint todo black coverage
