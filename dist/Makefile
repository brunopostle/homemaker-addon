VERSION:=`date '+%Y-%m-%d'`

dist:
	rm -rf homemaker
	rm -rf homemaker_tmp
	rm -rf working
	mkdir -p homemaker_tmp/libs/site/packages
	cp -r ../molior/ ../topologist/ ../__init__.py ../widgets.blend ../README.md ../LICENSE ../share/ homemaker_tmp/
	# cp ../blender_manifest.toml homemaker_tmp/
	rm -rf homemaker_tmp/*/__pycache__
	rm -rf homemaker_tmp/*/*/__pycache__
	rm -f homemaker_tmp/*/*.{orig,rej}
	rm -f homemaker_tmp/*/*/*.{orig,rej}
	mkdir -p working/wheels

	cd working/wheels && wget https://files.pythonhosted.org/packages/12/fc/a4d5a7554e0067677823f7265cb3ae22aed8a238560b5133b58cda252dad/PyYAML-6.0-cp39-cp39-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_12_x86_64.manylinux2010_x86_64.whl
	cd working/wheels && wget https://github.com/wassimj/Topologic/releases/download/v6.0.3/topologic_core-6.0.3-cp311-cp311-linux_x86_64.whl
	cd working/wheels && wget https://github.com/wassimj/Topologic/releases/download/v6.0.3/topologic_core-6.0.3-cp311-cp311-win_amd64.whl
	cd working/wheels && wget https://github.com/wassimj/Topologic/releases/download/v6.0.3/topologic_core-6.0.3-cp311-cp311-macosx_11_0_arm64.whl

	# MOLIOR WHEEL
	rm -rf ../build/
	cd .. && python -c "from setuptools import setup; \
	setup( \
		name='molior', \
		version='0.0.1', \
		author='Bruno Postle', \
		author_email='bruno@postle.net', \
		packages=['molior', 'molior.ifc', 'molior.style', 'molior.geometry'], \
		install_requires=['topologic_core', 'topologist', 'yaml', 'numpy', 'ifcopenshell'], \
	)" bdist_wheel
	mv molior-*-none-any.whl working/wheels/

	# TOPOLOGIST WHEEL
	rm -rf ../build/
	cd .. && python -c "from setuptools import setup; \
	setup( \
		name='topologist', \
		version='0.0.1', \
		author='Bruno Postle', \
		author_email='bruno@postle.net', \
		packages=['topologist', 'topologist.ushell', 'topologist.hulls', 'topologist.normals', \
		'topologist.ugraph', 'topologist.fitness', 'topologist.traces'], \
		install_requires=['topologic_core', 'numpy'], \
	)" bdist_wheel
	mv topologist-*-none-any.whl working/wheels/

	# YAML
	cd working && unzip wheels/PyYAML-6.0-*.whl
	cp -r working/yaml homemaker_tmp/libs/site/packages/
	rm homemaker_tmp/libs/site/packages/yaml/*.so

	# TOPOLOGIC
	cd working && unzip wheels/topologic_core-*-linux_x86_64.whl -d topologic-linux
	cd working && unzip wheels/topologic_core-*-win_amd64.whl -d topologic-win
	cd working && unzip wheels/topologic_core-*-macosx_11_0_arm64.whl -d topologic-darwin-arm

	# LINUX
	cp -a homemaker_tmp homemaker
	cp -a working/topologic-linux/topologic_core/ homemaker/libs/site/packages/
	cp -a working/topologic-linux/topologic_core.libs/ homemaker/libs/site/packages/
	zip -r blender-homemaker-$(VERSION)-linux-x86_64.zip ./homemaker
	rm -rf homemaker

	# WINDOWS
	cp -a homemaker_tmp homemaker
	cp -a working/topologic-win/topologic_core/ homemaker/libs/site/packages/
	zip -r blender-homemaker-$(VERSION)-win.zip ./homemaker
	rm -rf homemaker

	# MAC ARM
	cp -a homemaker_tmp homemaker
	cp -a working/topologic-darwin-arm/topologic_core/ homemaker/libs/site/packages/
	zip -r blender-homemaker-$(VERSION)-darwin-arm.zip ./homemaker
	rm -rf homemaker

	# NOARCH
	cp -a homemaker_tmp homemaker
	zip -r blender-homemaker-$(VERSION)-noarch.zip ./homemaker
	rm -rf homemaker

clean:
	rm -rf working homemaker_tmp

.PHONY: dist clean
