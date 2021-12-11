VERSION:=`date '+%Y-%m-%d'`

dist:
	rm -rf homemaker
	rm -rf homemaker_tmp
	rm -rf working
	mkdir -p homemaker_tmp/libs/site/packages
	cp -r ../molior/ ../topologist/ ../fitness/ ../__init__.py ../widgets.blend ../README.md ../LICENSE homemaker_tmp/
	rm -rf homemaker_tmp/*/__pycache__
	rm -rf homemaker_tmp/*/*/__pycache__
	mkdir -p working

	cd working && wget https://files.pythonhosted.org/packages/ac/dd/f6fc54a770ba0222261b33d60d9c9e01aa35d989f1cdfe892ae84e319779/ezdxf-0.16.3-cp39-cp39-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_12_x86_64.manylinux2010_x86_64.whl
	cd working && wget https://files.pythonhosted.org/packages/8a/bb/488841f56197b13700afd5658fc279a2025a39e22449b7cf29864669b15d/pyparsing-2.4.7-py2.py3-none-any.whl
	cd working && wget https://files.pythonhosted.org/packages/12/fc/a4d5a7554e0067677823f7265cb3ae22aed8a238560b5133b58cda252dad/PyYAML-6.0-cp39-cp39-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_12_x86_64.manylinux2010_x86_64.whl
	cd working && wget https://github.com/brunopostle/Topologic/releases/download/2021-10-31/Topologic_2021-10-31_linux.zip
	cd working && wget https://github.com/brunopostle/Topologic/releases/download/2021-10-31/Topologic_2021-10-31_darwin.zip
	cd working && wget https://github.com/brunopostle/Topologic/releases/download/2021-10-31/Topologic_2021-10-31_win.zip

	# EZDXF
	cd working && unzip ezdxf-0.16.3-*.whl
	cp -r working/ezdxf homemaker_tmp/libs/site/packages/
	rm homemaker_tmp/libs/site/packages/ezdxf/acc/*.so

	# PYPARSING
	cd working && unzip pyparsing-2.4.7-*.whl
	cp working/pyparsing.py homemaker_tmp/libs/site/packages/

	# YAML
	cd working && unzip PyYAML-6.0-*.whl
	cp -r working/yaml homemaker_tmp/libs/site/packages/
	rm homemaker_tmp/libs/site/packages/yaml/*.so

	# TOPOLOGIC
	cd working && unzip Topologic_*_linux.zip
	cd working && unzip Topologic_*_darwin.zip
	cd working && unzip Topologic_*_win.zip

	# LINUX
	cp -a homemaker_tmp homemaker
	cp working/Topologic_*_linux/* homemaker/libs/site/packages/
	zip -r blender-homemaker-$(VERSION)-linux-x86_64.zip ./homemaker
	rm -rf homemaker

	# WINDOWS
	cp -a homemaker_tmp homemaker
	cp working/Topologic_*_win/* homemaker/libs/site/packages/
	zip -r blender-homemaker-$(VERSION)-win.zip ./homemaker
	rm -rf homemaker

	# MAC
	cp -a homemaker_tmp homemaker
	cp working/Topologic_*_darwin/* homemaker/libs/site/packages/
	zip -r blender-homemaker-$(VERSION)-py39-darwin.zip ./homemaker
	rm -rf homemaker

	# NOARCH
	cp -a homemaker_tmp homemaker
	zip -r blender-homemaker-$(VERSION)-noarch.zip ./homemaker
	rm -rf homemaker

clean:
	rm -rf working homemaker_tmp

.PHONY: dist clean
