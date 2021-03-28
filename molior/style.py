import os, yaml


class style:
    def __init__(self, args={}):
        self.share_dir = "share"
        self.data = {}
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
                if ext == ".yml":
                    relpath = os.path.relpath(root, self.share_dir)
                    ancestors = list(reversed(relpath.split(os.sep)))
                    if not relpath == ".":
                        ancestors.append("default")
                    stylename = ancestors.pop(0)
                    if stylename == ".":
                        stylename = "default"

                    fh = open(os.path.join(root, name), "rb")
                    data = yaml.safe_load(fh.read())
                    fh.close()

                    data["ancestors"] = ancestors
                    if not stylename in self.data:
                        self.data[stylename] = {}
                    self.data[stylename][prefix] = data
