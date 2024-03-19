VERSION:=`date '+%Y-%m-%d'`

dist:
	rm -rf homemaker
	rm -rf homemaker_tmp
	rm -rf working
	mkdir -p homemaker_tmp/libs/site/packages
	cp -r ../molior/ ../topologist/ ../__init__.py ../widgets.blend ../README.md ../LICENSE ../blender_manifest.toml ../share/ homemaker_tmp/
	rm -rf homemaker_tmp/*/__pycache__
	rm -rf homemaker_tmp/*/*/__pycache__
	rm -f homemaker_tmp/*/*.{orig,rej}
	rm -f homemaker_tmp/*/*/*.{orig,rej}
	mkdir -p working

	cd working && wget https://files.pythonhosted.org/packages/12/fc/a4d5a7554e0067677823f7265cb3ae22aed8a238560b5133b58cda252dad/PyYAML-6.0-cp39-cp39-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_12_x86_64.manylinux2010_x86_64.whl
	cd working && wget https://github.com/brunopostle/Topologic/releases/download/2022-04-27/Topologic_2022-12-10_linux.zip
	cd working && wget https://github.com/brunopostle/Topologic/releases/download/2022-01-31/Topologic_2022-02-03_darwin.zip
	cd working && wget https://github.com/brunopostle/Topologic/releases/download/2022-04-27/Topologic_2022-04-10_win.zip
	cd working && wget https://github.com/brunopostle/Topologic/releases/download/2022-04-27/Topologic_2023-10-08_darwin-arm.zip

	# YAML
	cd working && unzip PyYAML-6.0-*.whl
	cp -r working/yaml homemaker_tmp/libs/site/packages/
	rm homemaker_tmp/libs/site/packages/yaml/*.so

	# TOPOLOGIC
	cd working && unzip Topologic_*_linux.zip
	cd working && unzip Topologic_*_darwin.zip
	cd working && unzip Topologic_*_win.zip
	cd working && unzip Topologic_*_darwin-arm.zip

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
	zip -r blender-homemaker-$(VERSION)-darwin.zip ./homemaker
	rm -rf homemaker

	# MAC ARM
	cp -a homemaker_tmp homemaker
	cp working/Topologic_*_darwin-arm/* homemaker/libs/site/packages/
	zip -r blender-homemaker-$(VERSION)-darwin-arm.zip ./homemaker
	rm -rf homemaker

	# NOARCH
	cp -a homemaker_tmp homemaker
	zip -r blender-homemaker-$(VERSION)-noarch.zip ./homemaker
	rm -rf homemaker

clean:
	rm -rf working homemaker_tmp

.PHONY: dist clean
