from urbane.formatters import IFormatter
from urbane.model import Signup
from urbane.utils import json_encode


class Formatter(IFormatter):

    def _handle_params_(self, data, data_root, **params):
        # handle `count` param
        count = 'count'
        if count in params:
            if isinstance(params[count], basestring) and params[count] != '':
                count = params[count]
            data[count] = len(data[data_root]) if isinstance(data[data_root], list) else 1
        # handle `total` param
        total = 'total'
        if total in params:
            if isinstance(params[total], basestring) and params[total] != '':
                total = params[total]
            data[total] = Signup.total(**params)
        return data


    def format(self, data, **params):
        if isinstance(data, list):
            data_root = params.pop('data_root', 'signups')
        elif isinstance(data, dict):
            data_root = params.pop('data_root', 'signup')
        else:
            return None
        return json_encode(self._handle_params_({ data_root: data }, data_root, **params))
