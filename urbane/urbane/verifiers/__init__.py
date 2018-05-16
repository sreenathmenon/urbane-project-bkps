from abc import ABCMeta, abstractmethod
from pecan import conf
from urbane.model import Signup

class IVerifier:

    __metaclass__ = ABCMeta

    def __call__(self, signup, **params):
        return self.verify(signup, **params)

    @abstractmethod
    def verify(self, signup, **params):
        pass
