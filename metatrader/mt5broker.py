from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import collections
import json

from backtrader import BrokerBase, OrderBase, Order
from backtrader.position import Position
from backtrader.utils.py3 import queue, with_metaclass

from .mt5store import MT5Store


class MT5Order(OrderBase):
    def __init__(self, owner, data, mt5_order):
        self.owner = owner
        self.data = data
        self.mt5_order = mt5_order
        self.ordtype = self.Buy if mt5_order['side'] == 'buy' else self.Sell
        self.size = float(mt5_order['amount'])

        super(MT5Order, self).__init__()


class MetaMT5Broker(BrokerBase.__class__):
    def __init__(cls, name, bases, dct):
        '''Class has already been created ... register'''
        # Initialize the class
        super(MetaMT5Broker, cls).__init__(name, bases, dct)
        MT5Store.BrokerCls = cls


class MT5Broker(with_metaclass(MetaMT5Broker, BrokerBase)):

    order_types = {Order.Market: 'market',
                   Order.Limit: 'limit',
                   Order.Stop: 'stop',
                   Order.StopLimit: 'stop limit'}

    def __init__(self, debug=False, **kwargs):
        super(MT5Broker, self).__init__()

        self.store = MT5Store(**kwargs)
        self.currency = self.store.currency
        self.positions = collections.defaultdict(Position)
        self.debug = debug
        self.indent = 4  # For pretty printing dictionaries
        self.notifs = queue.Queue()  # holds orders which are notified
        self.open_orders = list()
        self.startingcash = self.store._cash
        self.startingvalue = self.store._value

    def get_balance(self):
        self.store.get_balance()
        self.cash = self.store._cash
        self.value = self.store._value
        return self.cash, self.value

    def getcash(self):
        # Get cash seems to always be called before get value
        # Therefore it makes sense to add getbalance here.
        # return self.store.getcash(self.currency)
        self.cash = self.store._cash
        return self.cash

    def getvalue(self, datas=None):
        # return self.store.getvalue(self.currency)
        self.value = self.store._value
        return self.value

    def get_notification(self):
        try:
            return self.notifs.get(False)
        except queue.Empty:
            return None

    def notify(self, order):
        self.notifs.put(order)

    def getposition(self, data, clone=True):
        return self.store.getposition(data._dataname, clone=clone)
        # pos = self.positions[data._dataname]
        # if clone:
        #     pos = pos.clone()
        # return pos

    def next(self):

        if self.debug:
            print('Broker next() called')

    def _submit(self, owner, data, exectype, side, size, price, params):
        # get order type
        order_type = self.order_types.get(exectype) if exectype else 'market'

        _ret_ord = self.store.create_order(symbol=data.symbol, order_type=order_type, side=side,
                                          volume=size, price=price, params=params)

        # TODO check order retcode

        order = MT5Order(owner, data, _ret_ord)
        self.open_orders.append(order)

        self.notify(order)
        return order

    def buy(self, owner, data, size, price=None, plimit=None, exectype=None, valid=None,
            tradeid=0, oco=None, trailamount=None, trailpercent=None, **kwargs):
        del kwargs['parent']
        del kwargs['transmit']
        return self._submit(owner, data, exectype, 'buy', size, price, kwargs)

    def sell(self, owner, data, size, price=None, plimit=None, exectype=None, valid=None,
             tradeid=0, oco=None, trailamount=None, trailpercent=None, **kwargs):
        del kwargs['parent']
        del kwargs['transmit']
        return self._submit(owner, data, exectype, 'sell', size, price, kwargs)

    def cancel(self, order):
        oID = order.mt5_order['id']

        if self.debug:
            print('Broker cancel() called for {}'.format(order))

        # check first if the order has already been filled otherwise an error
        # might be raised if we try to cancel an order that is not open.
        # mt5_order = self.store.fetch_order(oID, order.data.symbol)
        # if self.debug:
        #     print(json.dumps(mt5_order, indent=self.indent))

        mt5_order = self.store.cancel_order(oID, order.data.symbol)

        # TODO conformation that order is canceled

        self.open_orders.remove(order)
        order.cancel()
        self.notify(order)
        return order

    def get_orders_open(self, safe=False):
        return self.store.fetch_open_orders()