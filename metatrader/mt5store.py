import backtrader as bt
import zmq
from backtrader.metabase import MetaParams
from backtrader.utils.py3 import with_metaclass


# TODO all requests to dict and check by key
# TODO wright functions comments
# TODO types


class MetaSingleton(MetaParams):
    '''Metaclass to make a metaclassed class a singleton'''

    def __init__(cls, name, bases, dct):
        super(MetaSingleton, cls).__init__(name, bases, dct)
        cls._singleton = None

    def __call__(cls, *args, **kwargs):
        if cls._singleton is None:
            cls._singleton = (
                super(MetaSingleton, cls).__call__(*args, **kwargs))

        return cls._singleton


class MT5Store(with_metaclass(MetaSingleton, object)):
    """
        Backtrader <-> Metatrader5 API.

        The MT5store class uses three ZeroMQ sockets to communicate with the server.
        1. (sys) First one sends commands to server. It receives back "ok" if the command was accomplished.
        2. (data) Second one is used to receive data from server.
        3. (live) Third socket is waiting for live data from the server on candle close.

    """
    HOST = 'localhost'
    SYS_PORT = 15555  # REP/REQ port
    DATA_PORT = 15556  # PUSH/PULL port
    LIVE_PORT = 15557  # PUSH/PULL port

    def __init__(self, currency, debug=False):
        self.currency = currency
        self.debug = debug
        self._cash = 0
        self._value = 0

    # ZeroMQ poller timeout in seconds
    # http://zguide.zeromq.org/py:mspoller
    poller_timeout = 10

    # initialise ZMQ context
    context = zmq.Context()
    # connect to server sockets
    try:
        sys_socket = context.socket(zmq.REQ)
        sys_socket.connect('tcp://{}:{}'.format(HOST, SYS_PORT))
        data_socket = context.socket(zmq.PULL)
        data_socket.connect('tcp://{}:{}'.format(HOST, DATA_PORT))
        live_socket = context.socket(zmq.PULL)
        live_socket.connect('tcp://{}:{}'.format(HOST, LIVE_PORT))
    except zmq.error as err:
        raise zmq.ZMQBindError("Error while ports binding...", err)

    # Supported granularities
    _GRANULARITIES = {
        (bt.TimeFrame.Minutes, 1): '1m',
        (bt.TimeFrame.Minutes, 5): '5m',
        (bt.TimeFrame.Minutes, 15): '15m',
        (bt.TimeFrame.Minutes, 30): '30m',
        (bt.TimeFrame.Minutes, 60): '1h',
        (bt.TimeFrame.Minutes, 120): '2h',
        (bt.TimeFrame.Minutes, 180): '3h',
        (bt.TimeFrame.Minutes, 240): '4h',
        (bt.TimeFrame.Minutes, 360): '6h',
        (bt.TimeFrame.Minutes, 480): '8h',
        (bt.TimeFrame.Minutes, 720): '12h',
        (bt.TimeFrame.Days, 1): '1d',
        (bt.TimeFrame.Weeks, 1): '1w',
        (bt.TimeFrame.Months, 1): '1M',
    }

    BrokerCls = None  # broker class will auto register
    DataCls = None  # data class will auto register

    def _send_request(self, data) -> None:
        """ Send request to ZeroMQ system socket """

        try:
            self.sys_socket.send_json(data)
            msg = self.sys_socket.recv_string()
            assert msg == 'OK', 'Something wrong on server side...'
        except:
            raise zmq.ZMQError("Something wrong while sending request...")

    def _pull_reply(self):
        """ Get reply from data socket with timeout """
        poller = zmq.Poller()
        poller.register(self.data_socket, zmq.POLLIN)
        # timeout in milliseconds
        if poller.poll(self.poller_timeout * 1000):
            msg = self.data_socket.recv_json()
        else:
            raise zmq.NotDone('Timeout was reached...')

        return msg

    def _live_data(self) -> list:
        """ Catch candles from server"""
        msg = self.live_socket.recv_json()
        return msg

    def _construct_and_send(self, **kwargs) -> dict:
        """ Construct JSON request dictionary from default """

        # default request dict
        request = {
            "action": None,
            "actionType": None,
            "symbol": None,
            "chartTF": None,
            "startTime": None,
            "id": None, 
            "price": None,
            "volume": None,
            "stoploss": None,
            "takeprofit": None,
            "deviation": None
        }

        # update dict values if exist
        for key, value in kwargs.items():
            if key in request:
                request[key] = value
            else:
                raise KeyError('Strange key passed in kwargs...')

        self._send_request(request)
        reply = self._pull_reply()

        return reply

    def _check_sockets(self):
        """ Check sockets connection  """
        request = self._create_dict(action="CHECK")

        self.sys_socket.send_json(request)
        sys = self.sys_socket.recv_json()
        data = self.data_socket.recv_json()
        live = self.live_socket.recv_json()

        print(sys, data, live)

        assert sys == 'OK', 'System socket is broken...'
        assert data == 'OK', 'Data socket is broken...'
        assert live == 'OK', 'Live socket is broken...'


    @classmethod
    def getdata(cls, *args, **kwargs):
        '''Returns ``DataCls`` with args, kwargs'''
        return cls.DataCls(*args, **kwargs)

    @classmethod
    def getbroker(cls, *args, **kwargs):
        '''Returns broker with *args, **kwargs from registered ``BrokerCls``'''
        return cls.BrokerCls(*args, **kwargs)

    def get_granularity(self, timeframe, compression):
        granularity = self._GRANULARITIES.get((timeframe, compression))
        if granularity is None:
            raise ValueError("Metatrader 5 doesn't support fetching OHLCV "
                             "data for time frame %s, comression %s" % \
                             (bt.TimeFrame.getname(timeframe), compression))
        return granularity

    def get_balance(self):
        balance = self._construct_and_send(action="BALANCE")
        if self.debug:
            print('Fetching balance: {}, Free: {}.'.format(balance['balance'], balance['equity']))
        self._cash = balance['equity']
        self._value = balance['balance']
        return balance

    def getposition(self):
        #return self._value
        try:
            positions = self._construct_and_send(action="POSITIONS_INFO")
        except:
            return None

        poslist = positions.get('positions', [])
        return poslist

    def create_order(self, symbol, order_type, side, amount, price=None, params=None):
        assert side in ['buy', 'sell'], 'Something wrong with order side...'
        # Convert Backtrader order names to MQL5 style
        # I use C style names as in the MQL5 script
        if order_type == 'market':
            actionType = 'ORDER_TYPE_BUY' if side == 'buy' else 'ORDER_TYPE_SELL'
        elif order_type == 'limit':
            actionType = 'ORDER_TYPE_BUY_LIMIT' if side == 'buy' else 'ORDER_TYPE_SELL_LIMIT'
        elif order_type == 'stop':
            actionType = 'ORDER_TYPE_BUY_STOP' if side == 'buy' else 'ORDER_TYPE_SELL_STOP'
        elif order_type == 'stop limit':
            actionType = 'ORDER_TYPE_BUY_STOP_LIMIT' if side == 'buy' else 'ORDER_TYPE_SELL_STOP_LIMIT'
        else:
            raise ValueError('Wrong order_type value...')

        confirmation = self._construct_and_send(action="TRADE", actionType=actionType, symbol=symbol,
                                  price=price, volume=amount, stoploss=None, takeprofit=None)

        if self.debug:
            print('Order confirmation: {}.'.format(confirmation))
        # returns the order conformation
        return confirmation

    def cancel_order(self, order_id, symbol):
        confirmation = self._construct_and_send(action="TRADE", actionType="CANCEL_ORDER", id=order_id, symbol=symbol)
        return confirmation

    def fetch_trades(self):
        return self._construct_and_send(action="FETCH_TRADES")

    def fetch_ohlcv(self, symbol, timeframe, since):
        candles = self._construct_and_send(action="HISTORY", symbol=symbol, chartTF=timeframe, startTime=since)
        if self.debug:
            print('Fetching: {}, TF: {}, Since: {}'.format(symbol, timeframe, since))
        return candles

    def fetch_open_orders(self):
        orders = self._construct_and_send(action="ORDERS_INFO")
        orders_list = orders.get('orders', [])
        if self.debug:
            print('Open orders: {}.'.format(orders))
        return orders_list
