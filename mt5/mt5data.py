from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from datetime import datetime

from backtrader.feed import DataBase
from backtrader import date2num, num2date
from backtrader.utils.py3 import queue, with_metaclass

from mt5 import mt5store


class MetaMTraderData(DataBase.__class__):
    def __init__(cls, name, bases, dct):
        """Class has already been created ... register"""
        # Initialize the class
        super(MetaMTraderData, cls).__init__(name, bases, dct)

        # Register with the store
        mt5store.MTraderStore.DataCls = cls


class MTraderData(with_metaclass(MetaMTraderData, DataBase)):
    """MTrader Data Feed.

    TODO: implement tick data
    TODO: test backfill_from

    Params:

      - `historical` (default: `False`)

        If set to `True` the data feed will stop after doing the first
        download of data.

        The standard data feed parameters `fromdate` and `todate` will be
        used as reference.

      - `backfill` (default: `True`)

        Perform backfilling after a disconnection/reconnection cycle. The gap
        duration will be used to download the smallest possible amount of data

      - `backfill_from` (default: `None`)

        An additional data source can be passed to do an initial layer of
        backfilling. Once the data source is depleted and if requested,
        backfilling from IB will take place. This is ideally meant to backfill
        from already stored sources like a file on disk, but not limited to.

      - `include_last` (default: `False`)

        Last historical candle is not closed. It will be updated in live stream

      - `reconnect` (default: `True`)

        Reconnect when network connection is down

    """
    params = (
        ('historical', False),   # do backfilling at the start
        ('backfill', True),      # do backfilling when reconnecting
        ('backfill_from', None), # additional data source to do backfill from
        ('include_last', False),
        ('reconnect', True),
    )

    _store = mt5store.MTraderStore

    # States for the Finite State Machine in _load
    _ST_FROM, _ST_START, _ST_LIVE, _ST_HISTORBACK, _ST_OVER = range(5)

    def islive(self):
        """True notifies `Cerebro` that `preloading` and `runonce`
        should be deactivated"""
        return True

    def __init__(self, **kwargs):
        self.o = self._store(**kwargs)
        # self._candleFormat = 'bidask' if self.p.bidask else 'midpoint'

    def setenvironment(self, env):
        """Receives an environment (cerebro) and passes it over to the store it
        belongs to"""
        super(MTraderData, self).setenvironment(env)
        env.addstore(self.o)

    def start(self):
        """Starts the MTrader connection and gets the real contract and
        contractdetails if it exists"""
        super(MTraderData, self).start()

        # Create attributes as soon as possible
        self._statelivereconn = False  # if reconnecting in live state
        self.qlive = self.o.q_livedata
        self._state = self._ST_OVER

        # Kickstart store and get queue to wait on
        self.o.start(data=self)

        # Check if the granularity is supported
        data_tf = self.o.get_granularity(self._timeframe, self._compression)
        if data_tf is None:
            self.put_notification(self.NOTSUPPORTED_TF)
            self._state = self._ST_OVER
            return

        # Configure server script symbol and time frame
        # Error will be raised if params are not supported
        self.o.config_server(self.p.dataname, data_tf)

        # Backfill from external data feed
        if self.p.backfill_from is not None:
            self._state = self._ST_FROM
            self.p.backfill_from._start()
        else:
            self._start_finish()
            # initial state for _load
            self._state = self._ST_START
            self._st_start()

    def _st_start(self):
        self.put_notification(self.DELAYED)

        date_begin = num2date(self.fromdate) if self.fromdate > float('-inf') else None
        date_end = num2date(self.todate) if self.todate < float('inf') else None

        self.qhist = self.o.candles(self.p.dataname, date_begin, date_end, self._timeframe,
                                    self._compression, self.p.include_last)

        self._state = self._ST_HISTORBACK

        return True

    def stop(self):
        '''Stops and tells the store to stop'''
        super(MTraderData, self).stop()
        self.o.stop()

    def haslivedata(self):
        return bool(self.qlive)  # do not return the obj

    def _load(self):
        if self._state == self._ST_OVER:
            return False

        while True:
            if self._state == self._ST_LIVE:
                try:
                    msg = self.qlive.get()
                except queue.Empty:
                    return None

                if msg:
                    if msg['status'] == 'DISCONNECTED':
                        self.put_notification(self.DISCONNECTED)

                        if not self.p.backfill:
                            self._state = self._ST_OVER

                        self._statelivereconn = True
                        continue

                    elif msg['status'] == 'CONNECTED' and self._statelivereconn:
                        self.put_notification(self.CONNECTED)
                        self._statelivereconn = False

                        if len(self) > 1:
                            self.fromdate = self.lines.datetime[-1]

                        self._st_start()
                        continue

                    if self._load_history(msg['data']):
                        return True  # loading worked

            elif self._state == self._ST_HISTORBACK:
                msg = self.qhist.get()
                if msg is None:
                    # Situation not managed. Simply bail out
                    self.put_notification(self.DISCONNECTED)
                    self._state = self._ST_OVER
                    return False  # error management cancelled the queue

                if msg:
                    if self._load_history(msg):
                        return True  # loading worked

                    continue  # not loaded ... date may have been seen
                else:
                    # End of histdata
                    if self.p.historical:  # only historical
                        self.put_notification(self.DISCONNECTED)
                        self._state = self._ST_OVER
                        return False  # end of historical

                # Live is also wished - go for it
                self._state = self._ST_LIVE
                self.put_notification(self.LIVE)
                continue

            elif self._state == self._ST_FROM:
                if not self.p.backfill_from.next():
                    # additional data source is consumed
                    self._state = self._ST_START
                    continue

                # copy lines of the same name
                for alias in self.lines.getlinealiases():
                    lsrc = getattr(self.p.backfill_from.lines, alias)
                    ldst = getattr(self.lines, alias)

                    ldst[0] = lsrc[0]

                return True

            elif self._state == self._ST_START:
                if not self._st_start():
                    self._state = self._ST_OVER
                    return False

    # def _load_tick(self, msg):
    #     dtobj = datetime.utcfromtimestamp(int(msg['time']))
    #     dt = date2num(dtobj)
    #     if dt <= self.lines.datetime[-1]:
    #         return False  # time already seen
    #
    #     # Common fields
    #     self.lines.datetime[0] = dt
    #     self.lines.volume[0] = 0.0
    #     self.lines.openinterest[0] = 0.0
    #
    #     # Put the prices into the bar
    #     tick = float(
    #         msg['askprice']) if self.p.useask else float(
    #         msg['bidprice'])
    #     self.lines.open[0] = tick
    #     self.lines.high[0] = tick
    #     self.lines.low[0] = tick
    #     self.lines.close[0] = tick
    #     self.lines.volume[0] = 0.0
    #     self.lines.openinterest[0] = 0.0
    #     return True

    def _load_history(self, ohlcv):
        time_stamp, _open, _high, _low, _close, _volume = ohlcv
        d_time = datetime.utcfromtimestamp(time_stamp)

        dt = date2num(d_time)
        # time already seen
        if dt <= self.lines.datetime[-1]:
            return False

        self.lines.datetime[0] = date2num(d_time)
        self.lines.open[0] = _open
        self.lines.high[0] = _high
        self.lines.low[0] = _low
        self.lines.close[0] = _close
        self.lines.volume[0] = _volume
        self.lines.openinterest[0] = 0.0
        return True
