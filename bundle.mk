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

        # roll-back to 29th April 2021 release (see #4)
	cd dist/working && wget https://files.pythonhosted.org/packages/51/8c/378b48e588359832b6a412cc63527a6af9fe797a92c6b726cedd442df7e8/cppyy_cling-6.21.7-py2.py3-none-manylinux2014_x86_64.whl
	cd dist/working && wget https://files.pythonhosted.org/packages/83/34/1d4a4a51909c2320c100e1d2aff47dbcb9efe3dfe4e1c150025a07027bfd/cppyy-backend-1.14.4.tar.gz
	cd dist/working && wget https://files.pythonhosted.org/packages/fb/cc/ca43218f5b8768e34a881605dcb899f6efe017915eacbc1c85de665f0864/CPyCppyy-1.12.5.tar.gz
	cd dist/working && wget https://files.pythonhosted.org/packages/ee/7e/ee06951cc63c14e708357f6d9ee1a9eff6cdf48b5d51e4de87db9c6ba071/cppyy-1.9.6.tar.gz

	cd dist/working && wget https://files.pythonhosted.org/packages/ac/dd/f6fc54a770ba0222261b33d60d9c9e01aa35d989f1cdfe892ae84e319779/ezdxf-0.16.3-cp39-cp39-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_12_x86_64.manylinux2010_x86_64.whl
	cd dist/working && wget https://files.pythonhosted.org/packages/8a/bb/488841f56197b13700afd5658fc279a2025a39e22449b7cf29864669b15d/pyparsing-2.4.7-py2.py3-none-any.whl
	cd dist/working && wget https://github.com/brunopostle/Topologic/releases/download/2021-06-15/TopologicCore-2021-06-15-manylinux_2_24-x86_64.zip
	cd dist/working && wget -O topologicPy-master.zip https://github.com/brunopostle/topologicPy/archive/refs/heads/master.zip

	# TOPOLOGIC

	# topologicPy
	cd dist/working && unzip topologicPy-master.zip
	cp -r dist/working/topologicPy-master/cpython/topologic dist/homemaker/libs/site/packages/
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
	cd dist/working/cppyy-backend-1.14.4/ && PYTHONPATH=../../homemaker/libs/site/packages python setup.py build && cp -r build/lib.*/cppyy_backend/lib/* ../../homemaker/libs/site/packages/cppyy_backend/lib/

	cd dist/working && tar -xzvf CPyCppyy-*.tar.gz
	cd dist/working/CPyCppyy-1.12.5/ && PYTHONPATH=../../homemaker/libs/site/packages python setup.py build && cp -r build/lib.*/* ../../homemaker/libs/site/packages/ && cp -r include/CPyCppyy ../../homemaker/libs/site/packages/topologic/include/api/

	# set rpath to find bundled libpython
	patchelf --set-rpath '$$ORIGIN/.' dist/homemaker/libs/site/packages/libcppyy.*.so

	cd dist/working && tar -xzvf cppyy-1.9.6.tar.gz
	cd dist/working/cppyy-1.9.6/ && PYTHONPATH=../../homemaker/libs/site/packages python setup.py build && cp -r build/lib/cppyy ../../homemaker/libs/site/packages/

	# libpython needed with 3.7, but not 3.9 ??!?
	if [ -e /usr/local/lib/libpython3.7m.so.1.0 ]; then cp /usr/local/lib/libpython3.7m.so.1.0 dist/homemaker/libs/site/packages/; fi
	if [ -e /usr/lib64/libpython3.7m.so.1.0 ]; then cp /usr/lib64/libpython3.7m.so.1.0 dist/homemaker/libs/site/packages/; fi

	strip dist/homemaker/libs/site/packages/cppyy_backend/lib/*.so
	strip dist/homemaker/libs/site/packages/*.so

	# bundle some libc++ headers
	mv dist/working/TopologicCore-*/include/c++/* dist/homemaker/libs/site/packages/cppyy_backend/include/

	# generate PCH (cppyy pre-compiled headers) file
	PYTHONPATH=dist/homemaker/libs/site/packages python -c 'import topologic'
	chmod 775 dist/homemaker/libs/site/packages/cppyy_backend/bin/rootcling

	# EZDXF

	cd dist/working && unzip ezdxf-0.16.3-*.whl
	cp -r dist/working/ezdxf dist/homemaker/libs/site/packages/

	cd dist/working && unzip pyparsing-2.4.7-*.whl
	cp dist/working/pyparsing.py dist/homemaker/libs/site/packages/

	# PyYAML

	pip install PyYAML -t dist/homemaker/libs/site/packages/

	cd dist && zip -r blender-homemaker-$(VERSION)-$(PYVERSION)-$(PLATFORM).zip ./homemaker
	#rm -rf dist/homemaker
	#rm -rf dist/working

clean:
	rm -rf dist

.PHONY: dist clean
