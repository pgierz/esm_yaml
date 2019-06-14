import yaml

class Config(object):
    def __init__(self, path):
        config = yaml.read(path)