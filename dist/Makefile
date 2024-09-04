VERSION := 0.$(shell date '+%Y%m%d').0

dist:
	rm -rf homemaker
	mkdir -p homemaker/wheels
	cp -r ../__init__.py ../widgets.blend ../README.md ../LICENSE ../share/ ../molior/ ../topologist/ ../blender_manifest.toml homemaker/
	rm -f homemaker/*.{orig,rej}
	rm -f homemaker/*/*.{orig,rej}
	rm -f homemaker/*/*/*.{orig,rej}
	rm -f homemaker/*/*/*/*.{orig,rej}
	rm -rf homemaker/__pycache__
	rm -rf homemaker/*/__pycache__
	rm -rf homemaker/*/*/__pycache__

	cd homemaker/wheels && wget https://files.pythonhosted.org/packages/ed/23/8da0bbe2ab9dcdd11f4f4557ccaf95c10b9811b13ecced089d43ce59c3c8/PyYAML-6.0.2-cp311-cp311-win_amd64.whl
	cd homemaker/wheels && wget https://files.pythonhosted.org/packages/75/e4/2c27590dfc9992f73aabbeb9241ae20220bd9452df27483b6e56d3975cc5/PyYAML-6.0.2-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
	cd homemaker/wheels && wget https://files.pythonhosted.org/packages/8b/62/b9faa998fd185f65c1371643678e4d58254add437edb764a08c5a98fb986/PyYAML-6.0.2-cp311-cp311-macosx_11_0_arm64.whl
	cd homemaker/wheels && wget https://github.com/wassimj/Topologic/releases/download/v6.0.3/topologic_core-6.0.3-cp311-cp311-linux_x86_64.whl
	cd homemaker/wheels && wget https://github.com/wassimj/Topologic/releases/download/v6.0.3/topologic_core-6.0.3-cp311-cp311-win_amd64.whl
	cd homemaker/wheels && wget https://github.com/wassimj/Topologic/releases/download/v6.0.3/topologic_core-6.0.3-cp311-cp311-macosx_11_0_arm64.whl

	# EXTENSION
	sed -i 's/version = "0.0.1"/version = "$(VERSION)"/' homemaker/blender_manifest.toml
	rm -f add-on-homemaker-v$(VERSION).zip
	zip -r add-on-homemaker-v$(VERSION).zip ./homemaker

clean:
	rm -rf homemaker

.PHONY: dist clean
