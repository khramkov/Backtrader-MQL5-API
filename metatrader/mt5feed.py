from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from collections import deque
from datetime import datetime

import backtrader as bt
from backtrader.feed import DataBase
from backtrader.utils.py3 import with_metaclass

from .mt5store import MT5Store


class MetaMT5Store(DataBase.__class__):
    def __init__(cls, name, bases, dct):
        '''Class has already been created ... register'''
        # Initialize the class
        super(MetaMT5Store, cls).__init__(name, bases, dct)

        # Register with the store
        MT5Store.DataCls = cls


class MT5Feed(with_metaclass(MetaMT5Store, DataBase)):
    params = (
        # only historical download
        ('historical', False),
        ('debug', True),
    )

    _store = MT5Store

    # States for the Finite State Machine in _load
    _ST_LIVE, _ST_HISTORBACK, _ST_OVER = range(3)

    def __init__(self, **kwargs):
        self.symbol = self.p.dataname
        self.store = self._store(**kwargs)
        self._data = deque()  # data queue for price data
        self._last_id = ''  # last processed trade id for ohlcv
        self._last_ts = 0  # last processed timestamp for ohlcv

    def start(self, ):
        DataBase.start(self)

        if self.p.fromdate:
            self._state = self._ST_HISTORBACK
            self.put_notification(self.DELAYED)
            self._fetch_ohlcv(self.p.fromdate)

        else:
            self._state = self._ST_LIVE
            self.put_notification(self.LIVE)

    def _load(self):
        if self._state == self._ST_OVER:
            return False

        while True:
            if self._state == self._ST_LIVE:
                if self._timeframe == bt.TimeFrame.Ticks:
                    return self._load_ticks()
                else:
                    ohlcv = self.store._live_data()
                    tstamp = ohlcv[0]

                    if tstamp > self._last_ts:
                        if self.p.debug:
                            print('Adding: {}'.format(ohlcv))
                        self._data.append(ohlcv)
                        self._last_ts = tstamp
                    ret = self._load_ohlcv()
                    return ret

            elif self._state == self._ST_HISTORBACK:
                ret = self._load_ohlcv()
                if ret:
                    return ret
                else:
                    # End of historical data
                    if self.p.historical:  # only historical
                        self.put_notification(self.DISCONNECTED)
                        self._state = self._ST_OVER
                        return False  # end of historical
                    else:
                        self._state = self._ST_LIVE
                        self.put_notification(self.LIVE)
                        continue

    def _fetch_ohlcv(self, fromdate=None):
        """Fetch OHLCV data into self._data queue"""
        granularity = self.store.get_granularity(self._timeframe, self._compression)

        if fromdate:
            since = int((fromdate - datetime(1970, 1, 1)).total_seconds())
        else:
            if self._last_ts > 0:
                since = self._last_ts
            else:
                since = None

        # TODO if one candle missed
        # TODO check last historical candle is closed

        data = self.store.fetch_ohlcv(self.symbol, timeframe=granularity,
                                      since=since)

        if self.p.debug:
            since_dt = datetime.fromtimestamp(since) if since is not None else 'NA'
            print('---- NEW REQUEST ----')
            print('{} - Requesting: Since date {} granularity {}'.format(
                datetime.now(), since_dt, granularity))

            try:
                for i, ohlcv in enumerate(data):
                    tstamp, open_, high, low, close, volume = ohlcv
                    print('{} - Data {}: {}'.format(datetime.now(), i, datetime.utcfromtimestamp(tstamp)))
            except IndexError:
                print('Index Error: Data = {}'.format(data))
            print('---- REQUEST END ----')

        for ohlcv in data:

            if None in ohlcv:
                continue

            tstamp = ohlcv[0]

            if tstamp > self._last_ts:
                if self.p.debug:
                    print('Adding: {}'.format(ohlcv))
                self._data.append(ohlcv)
                self._last_ts = tstamp

    def _load_ohlcv(self):
        try:
            ohlcv = self._data.popleft()
        except IndexError:
            return None  # no data in the queue

        tstamp, open_, high, low, close, volume = ohlcv

        dtime = datetime.fromtimestamp(tstamp)

        self.lines.datetime[0] = bt.date2num(dtime)
        self.lines.open[0] = open_
        self.lines.high[0] = high
        self.lines.low[0] = low
        self.lines.close[0] = close
        self.lines.volume[0] = volume

        return True

    def haslivedata(self):
        return self._state == self._ST_LIVE and self._data

    def islive(self):
        return not self.p.historical
