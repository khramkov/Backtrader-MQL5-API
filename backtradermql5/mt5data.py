from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import datetime

from backtrader.feed import DataBase
from backtrader import date2num, num2date
from backtrader.utils.py3 import queue, with_metaclass

from backtradermql5 import mt5store


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

      - `useask` (default: `False`)

        When requsting tick data use the ask price instead of the default bid price.
        Only works with tick data.

      - `addspread` (default: `False`)

        Add spread difference to candle price data.
        Only works with candle data.

    """

    params = (
        ("historical", False),  # do backfilling at the start
        ("backfill", True),  # do backfilling when reconnecting
        ("backfill_from", None),  # additional data source to do backfill from
        ("include_last", False),
        ("reconnect", True),
        ("useask", False),  # use the ask price instead of the default
        ("addspread", False),  # add spread difference to candle price data
    )

    _store = mt5store.MTraderStore

    # States for the Finite State Machine in _load
    _ST_FROM, _ST_START, _ST_LIVE, _ST_HISTORBACK, _ST_OVER = range(5)

    _historyback_queue_size = 0

    def islive(self):
        """True notifies `Cerebro` that `preloading` and `runonce`
        should be deactivated"""
        return True

    def __init__(self, **kwargs):
        self.o = self._store(**kwargs)

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

        # Add server script symbol and time frame
        self.o.config_server(self.p.dataname, self.p.timeframe, self.p.compression)

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

        date_begin = num2date(self.fromdate) if self.fromdate > float("-inf") else None
        date_end = num2date(self.todate) if self.todate < float("inf") else None

        self.qhist = self.o.price_data(
            self.p.dataname, date_begin, date_end, self.p.timeframe, self.p.compression, self.p.include_last,
        )

        self._state = self._ST_HISTORBACK

        return True

    def stop(self):
        """Stops and tells the store to stop"""
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
                    if msg["status"] == "DISCONNECTED":
                        self.put_notification(self.DISCONNECTED)

                        if not self.p.backfill:
                            self._state = self._ST_OVER

                        self._statelivereconn = True
                        continue

                    elif msg["status"] == "CONNECTED" and self._statelivereconn:
                        self.put_notification(self.CONNECTED)
                        self._statelivereconn = False

                        if len(self) > 1:
                            self.fromdate = self.lines.datetime[-1]

                        self._st_start()
                        continue

                    if (
                        msg["timeframe"] == self.o.get_granularity(self.p.timeframe, self.p.compression)
                        and msg["symbol"] == self.p.dataname
                    ):
                        if msg["timeframe"] == "TICK":
                            if self._load_tick(msg["data"]):
                                return True  # loading worked
                        else:
                            if self._load_candle(msg["data"]):
                                return True  # loading worked

            elif self._state == self._ST_HISTORBACK:
                msg = self.qhist.get()
                # Queue size of historical price data
                self._historyback_queue_size = self.qhist.qsize()
                if msg is None:
                    # Situation not managed. Simply bail out
                    self.put_notification(self.DISCONNECTED)
                    self._state = self._ST_OVER
                    return False  # error management cancelled the queue
                if msg and self.p.timeframe == 1:  # if timeframe is ticks
                    if self._load_tick(msg):
                        return True  # loading worked
                elif msg:
                    if self._load_candle(msg):
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

    def _load_tick(self, msg):
        time_stamp, _bid, _ask = msg
        # convert unix timestamp to float for millisecond resolution
        d_time = datetime.utcfromtimestamp(float(time_stamp) / 1000.0)

        dt = date2num(d_time)

        # time already seen
        if dt <= self.lines.datetime[-1]:
            return False

        # Common fields
        self.lines.datetime[0] = dt
        self.lines.volume[0] = 0.0
        self.lines.openinterest[0] = 0.0

        # Put the prices into the bar
        tick = float(_ask) if self.p.useask else float(_bid)
        self.lines.open[0] = tick
        self.lines.high[0] = tick
        self.lines.low[0] = tick
        self.lines.close[0] = tick

        return True

    def _load_candle(self, ohlcv):
        time_stamp, _open, _high, _low, _close, _volume, _spread = ohlcv
        d_time = datetime.utcfromtimestamp(time_stamp)

        dt = date2num(d_time)

        # time already seen
        if dt <= self.lines.datetime[-1]:
            return False

        def addspread(p, s):
            if self.p.dataname.endswith("JPY"):
                return round(sum([float(p), int(s) * 0.001]), 3)
            else:
                return round(sum([float(p), int(s) * 0.00001]), 5)

        self.lines.datetime[0] = dt
        self.lines.open[0] = _open if not self.p.addspread else addspread(_open, _spread)
        self.lines.high[0] = _high if not self.p.addspread else addspread(_high, _spread)
        self.lines.low[0] = _low if not self.p.addspread else addspread(_low, _spread)
        self.lines.close[0] = _close if not self.p.addspread else addspread(_close, _spread)
        self.lines.volume[0] = _volume
        self.lines.openinterest[0] = 0.0
        return True
