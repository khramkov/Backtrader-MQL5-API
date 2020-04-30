import pytz
import backtrader as bt
import backtrader.indicators as btind
from backtradermql5.mt5store import MTraderStore
from backtradermql5.mt5indicator import getMTraderIndicator
from backtradermql5.mt5chart import MTraderChart
from datetime import datetime, timedelta

HOST = '192.168.1.83'


class SmaCross(bt.SignalStrategy):

    def __init__(self, store):
        self.buy_order = None
        self.live_data = False

        # You can hookup backtrader to any indicator that runs in MT5
        # Startup and retrieve values from the MT5 indicator "Examples/Envelopes"
        self.mt5macd = getMTraderIndicator(
            # MTraderStorestore instance
            store,
            # Data stream to run the indicator calculations on
            self.datas[0],
            # Set accessor(s) for the indicator output
            ("val1", "val2",),
            # MT5 inidicator name
            indicator="Examples/MACD",
            # Indicator parameters.
            # Any omitted values will use the defaults as defind by the indicator
            params=[12, 26, 9, 'PRICE_CLOSE']
        )()

        # Attach any inidcator to be drawn to a chart window before instantiating the MTraderChart class.
        self.sma = btind.SimpleMovingAverage(self.data)

        # Open a new chart window in MT5 with symbol and timeframe provided by the passed data stream object.
        # Important: create a new chart instance only after you attached any
        # indicator you want to draw to avoid errors.
        chart = MTraderChart(data_obj=self.datas[0])

        # Draw the SMA indicator to a chart instance in MT5.
        chart.addline(self.sma,
                      style={'shortname': 'BT-SMA', 'color': 'clrBlue'})

    def next(self):
        if self.buy_order is None:
            self.buy_order = self.buy_bracket(
                limitprice=1.13, stopprice=1.10, size=0.1, exectype=bt.Order.Market)

        if self.live_data:
            cash = self.broker.getcash()

            # Cancel order
            if self.buy_order is not None:
                self.cancel(self.buy_order[0])

        else:
            # Avoid checking the balance during a backfill. Otherwise, it will
            # Slow things down.
            cash = 'NA'

        for data in self.datas:
            print(
                f'{data.datetime.datetime()} - {data._name} | Cash {cash} | O: {data.open[0]} H: {data.high[0]} L: {data.low[0]} C: {data.close[0]} V:{data.volume[0]}')
            print(
                f'Examples/Envelopes {self.mt5macd.val1[0]} {self.mt5macd.val2[0]}')

    def notify_data(self, data, status, *args, **kwargs):
        dn = data._name
        dt = datetime.now()
        msg = f'Data Status: {data._getstatusname(status)}'
        print(dt, dn, msg)
        if data._getstatusname(status) == 'LIVE':
            self.live_data = True
        else:
            self.live_data = False


host = '192.168.1.83'

cerebro = bt.Cerebro()
store = MTraderStore(host=host, debug=True, datatimeout=10)
cerebro.addstrategy(SmaCross, store)

# uncomment next 2 lines to use backbroker for live trading with MTraderStore
# broker = store.getbroker(use_positions=True)
# cerebro.setbroker(broker)

start_date = datetime.now() - timedelta(minutes=200)

data = store.getdata(dataname='EURUSD',
                     timeframe=bt.TimeFrame.Minutes,
                     fromdate=start_date,
                     compression=5,
                     tz=pytz.timezone('Europe/Berlin'),
                     # useask=True, # ask price instead if the default bid price
                     # addspread=True, # add the spread value
                     historical=True
                     )

cerebro.adddata(data)

cerebro.run(stdstats=False)
