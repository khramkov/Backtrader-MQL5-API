import pprint
from datetime import datetime


class Adapter(object):
    def __init__(self, raw):
        self._raw = raw

    def __getattr__(self, key):
        if key in self._raw:
            val = self._raw[key]
            if isinstance(val, (int or float)) and key.endswith('_time'):
                return datetime.utcfromtimestamp(val)
            else:
                return val
        return super().__getattribute__(key)

    def __repr__(self):
        return '{name}({raw})'.format(
            name=self.__class__.__name__,
            raw=pprint.pformat(self._raw, indent=4),
        )


class BalanceAdapter(Adapter):
    pass


class OrderAdapter(Adapter):
    pass


class PositionAdapter(Adapter):
    pass
