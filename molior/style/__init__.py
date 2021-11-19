"""A folder tree of inheritable style definitions and resources

A 'style' is defined by a collection of YAML configuration files and other file
resources in a folder.  This module provides methods for accessing this data.

Alternative styles are accessed by a stylename, each represented by a subfolder
that inherits data and resources from all parent folders.  For example, a style
named 'thin' may be found in a folder named ${share_dir}/rustic/wood/thin; any
query for 'thin' data not found in this folder will be sought in
${share_dir}/rustic/wood; failing that it will be sought in
${share_dir}/rustic, and finally in ${share_dir} itself.

Note that styles are accessed by their short stylename _not_ the path, this
allows inheritance to be defined entirely by rearrangement of the configuration
data.  This also means that there may only be one folder called 'thin' in the
folder tree, all others will be ignored.

"""

import os, yaml, copy, json


class Style:
    def __init__(self, args=None):
        """Read all the data in ${share_dir} and sub-folders, collect names of
        non-YAML files. Default location is a folder called 'share' installed with this
        module, or pass an absolute path in the 'share_dir' parameter to indicate a
        different collection of styles."""
        if args is None:
            args = {}
        self.share_dir = "share"
        self.data = {}
        self.files = {}
        for arg in args:
            self.__dict__[arg] = args[arg]

        if not os.path.isabs(self.share_dir):
            self.share_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), self.share_dir)
            )
        self.share_dir = os.path.normpath(self.share_dir)
        # share_dir should now be an absolute path
        # slurp all the yaml data under share_dir
        for root, dirs, files in os.walk(self.share_dir):
            for name in files:
                prefix, ext = os.path.splitext(name)
                relpath = os.path.relpath(root, self.share_dir)
                ancestors = list(reversed(relpath.split(os.sep)))
                if not relpath == ".":
                    ancestors.append("default")
                stylename = ancestors.pop(0)
                if stylename == ".":
                    stylename = "default"

                if not stylename in self.data:
                    self.data[stylename] = {}
                if not stylename in self.files:
                    self.files[stylename] = {}
                # TODO convert files to json, then remove yaml support
                if ext == ".yml":
                    fh = open(os.path.join(root, name), "rb")
                    data = yaml.safe_load(fh.read())
                    fh.close()

                    self.data[stylename][prefix] = data
                    self.data[stylename]["ancestors"] = ancestors
                if ext == ".json":
                    with open(os.path.join(root, name)) as fh:
                        data = json.load(fh)

                    self.data[stylename][prefix] = data
                    self.data[stylename]["ancestors"] = ancestors
                else:
                    self.files[stylename][name] = os.path.join(root, name)

    def get(self, stylename):
        """retrieves a flattened style definition with ancestors filling in the gaps"""
        # FIXME this results in duplicated assets when an ancestor style is also in use
        if not stylename in self.data:
            return self.get("default")
        mydata = copy.deepcopy(self.data[stylename])
        if len(mydata["ancestors"]) == 0:
            return mydata
        ancestor = self.get(mydata["ancestors"][0])
        for key in ancestor:
            if not key == "ancestors":
                if key in mydata:
                    ancestor[key].update(mydata[key])
        return ancestor

    def get_file(self, stylename, filename):
        """retrieves a file path for a filename with ancestors filling in the gaps"""
        if not stylename in self.files:
            return self.get_file("default", filename)
        if len(self.data[stylename]["ancestors"]) == 0:
            if filename in self.files[stylename]:
                return self.files[stylename][filename]
            return None
        if filename in self.files[stylename]:
            return self.files[stylename][filename]
        else:
            return self.get_file(self.data[stylename]["ancestors"][0], filename)
