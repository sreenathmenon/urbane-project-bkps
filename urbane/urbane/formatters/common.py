from urbane.formatters import IFormatter
from urbane.model import Signup
from urbane.utils import json_encode

class Formatter(IFormatter):

    def format(self, data, **kwargs):
        data_root = kwargs.pop('data_root', None)
        _data_ = { data_root: data } if data_root else data

        print data
        print '>>>>>>>>>>>>>>>>>>>>>>>>>'
        return json_encode(_data_)
