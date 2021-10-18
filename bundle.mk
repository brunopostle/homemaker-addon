VERSION:=`date '+%Y-%m-%d'`
PYVERSION:=`python --version | sed 's/Python /py/' | sed 's/\.[0-9]\+$$//' | sed 's/\.//'`
PLATFORM:=linux-x86_64

dist:
	rm -rf dist/homemaker
	rm -rf dist/working
	mkdir -p dist/homemaker/libs/site/packages
	cp -r molior/ topologist/ __init__.py dist/homemaker/
	rm -rf dist/homemaker/*/__pycache__
	rm -rf dist/homemaker/*/*/__pycache__
	mkdir -p dist/working

	cd dist/working && wget https://files.pythonhosted.org/packages/ac/dd/f6fc54a770ba0222261b33d60d9c9e01aa35d989f1cdfe892ae84e319779/ezdxf-0.16.3-cp39-cp39-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_12_x86_64.manylinux2010_x86_64.whl
	cd dist/working && wget https://files.pythonhosted.org/packages/8a/bb/488841f56197b13700afd5658fc279a2025a39e22449b7cf29864669b15d/pyparsing-2.4.7-py2.py3-none-any.whl
	cd dist/working && wget https://github.com/brunopostle/Topologic-1/releases/download/2021-10-18/Topologic_2021-10-18_buster.zip

	# TOPOLOGIC

	cd dist/working && unzip Topologic_*_buster.zip
	cp dist/working/Topologic_*_buster/* dist/homemaker/libs/site/packages/

	# EZDXF

	cd dist/working && unzip ezdxf-0.16.3-*.whl
	cp -r dist/working/ezdxf dist/homemaker/libs/site/packages/

	cd dist/working && unzip pyparsing-2.4.7-*.whl
	cp dist/working/pyparsing.py dist/homemaker/libs/site/packages/

	# PyYAML

	pip install PyYAML -t dist/homemaker/libs/site/packages/

	cd dist && zip -r blender-homemaker-$(VERSION)-$(PLATFORM).zip ./homemaker
	#rm -rf dist/homemaker
	#rm -rf dist/working

clean:
	rm -rf dist

.PHONY: dist clean
