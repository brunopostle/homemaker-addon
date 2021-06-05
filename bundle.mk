VERSION:=`date '+%Y-%m-%d'`
PYVERSION:=py39
PLATFORM:=linux-x86_64

dist:
	rm -rf dist/homemaker
	#rm -rf dist
	mkdir -p dist/homemaker/libs/site/packages
	cp -r molior/ topologist/ __init__.py dist/homemaker/
	rm -rf dist/homemaker/*/__pycache__
	rm -rf dist/homemaker/*/*/__pycache__
	mkdir -p dist/working

	cd dist/working && wget https://files.pythonhosted.org/packages/94/0b/960513ec1b582793e92dafb7915c6498d688fd619f79691916b84f2f3bee/cppyy_cling-6.25.0-py2.py3-none-manylinux2014_x86_64.whl
	cd dist/working && wget https://files.pythonhosted.org/packages/85/15/f7a4b706c6b91045ee3c865ae593ddf077a463914aadddbe803c0c11992a/cppyy-backend-1.14.5.tar.gz
	cd dist/working && wget https://files.pythonhosted.org/packages/ed/a2/75e715ec671bd491729fb208b9757239148b7efe02d801032eab30c19846/CPyCppyy-1.12.6.tar.gz
	cd dist/working && wget https://files.pythonhosted.org/packages/81/3d/cf40833ecb8f2ae7024a8aeead8d5f699c3350cbf57582f087900ca0dddf/cppyy-2.0.0.tar.gz
	cd dist/working && wget https://files.pythonhosted.org/packages/ac/dd/f6fc54a770ba0222261b33d60d9c9e01aa35d989f1cdfe892ae84e319779/ezdxf-0.16.3-cp39-cp39-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_12_x86_64.manylinux2010_x86_64.whl
	cd dist/working && wget https://files.pythonhosted.org/packages/8a/bb/488841f56197b13700afd5658fc279a2025a39e22449b7cf29864669b15d/pyparsing-2.4.7-py2.py3-none-any.whl
	#cd dist/working && wget https://files.pythonhosted.org/packages/ba/d4/3cf562876e0cda0405e65d351b835077ab13990e5b92912ef2bf1a2280e0/PyYAML-5.4.1-cp27-cp27mu-manylinux1_x86_64.whl
	cd dist/working && wget https://github.com/brunopostle/Topologic/releases/download/2021-06-01/TopologicCore-2021-06-01-manylinux_2_24-x86_64.zip

	# TOPOLOGIC

	# topologicPy
	cp -r ~/src/topologicPy/cpython/topologic/ dist/homemaker/libs/site/packages/
	mkdir dist/homemaker/libs/site/packages/topologic/lib
	mkdir -p dist/homemaker/libs/site/packages/topologic/include/api

        # pre-compiled TopologicCore
	cd dist/working && unzip TopologicCore-*.zip
	cp -r dist/working/TopologicCore-*/lib/* dist/homemaker/libs/site/packages/topologic/lib/
	cp -r dist/working/TopologicCore-*/include/* dist/homemaker/libs/site/packages/topologic/include/

	# CPPYY

	cd dist/working && unzip cppyy_cling-*.whl
	cp -r dist/working/cppyy_backend dist/homemaker/libs/site/packages/

	cd dist/working && tar -xzvf cppyy-backend-*.tar.gz
	cd dist/working/cppyy-backend-1.14.5/ && PYTHONPATH=../../homemaker/libs/site/packages python setup.py build && cp -r build/lib.*/cppyy_backend/lib/* ../../homemaker/libs/site/packages/cppyy_backend/lib/

	cd dist/working && tar -xzvf CPyCppyy-*.tar.gz
	cd dist/working/CPyCppyy-1.12.6/ && PYTHONPATH=../../homemaker/libs/site/packages python setup.py build && cp -r build/lib.*/* ../../homemaker/libs/site/packages/ && cp -r include/CPyCppyy ../../homemaker/libs/site/packages/topologic/include/api/

	cd dist/working && tar -xzvf cppyy-2.0.0.tar.gz
	cd dist/working/cppyy-2.0.0/ && PYTHONPATH=../../homemaker/libs/site/packages python setup.py build && cp -r build/lib/cppyy ../../homemaker/libs/site/packages/

	strip dist/homemaker/libs/site/packages/cppyy_backend/lib/*.so
	strip dist/homemaker/libs/site/packages/*.so

	# EZDXF

	cd dist/working && unzip ezdxf-0.16.3-*.whl
	cp -r dist/working/ezdxf dist/homemaker/libs/site/packages/

	cd dist/working && unzip pyparsing-2.4.7-*.whl
	cp dist/working/pyparsing.py dist/homemaker/libs/site/packages/

	#cd dist/working && unzip PyYAML-*.whl
	#cp -r dist/working/yaml dist/homemaker/libs/site/packages/
	pip install PyYAML -t dist/homemaker/libs/site/packages/

	cd dist && zip -r blender-homemaker-$(VERSION)-$(PYVERSION)-$(PLATFORM).zip ./homemaker
	#rm -rf dist/homemaker
	#rm -rf dist/working

clean:
	rm -rf dist

.PHONY: dist clean
