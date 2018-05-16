from abc import ABCMeta, abstractmethod
from pecan import conf
from urbane.model import Signup

class IFormatter:

    __metaclass__ = ABCMeta

    def __init__(self, **config):
        pass

    def __call__(self, data, **kwargs):
        return self.format(data, **kwargs)

    @abstractmethod
    def format(self, data, **kwargs):
        pass
