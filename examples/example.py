import backtrader as bt
import backtrader.indicators as btind
from backtradermql5.mt5store import MTraderStore
from backtradermql5.mt5indicator import getMTraderIndicator
from backtradermql5.mt5chart import MTraderChart
from datetime import datetime, timedelta

HOST = '192.168.1.83'


class SmaCross(bt.SignalStrategy):

    def __init__(self, store):
        # self.mt = dict()
        self.buy_order = None
        self.live_data = False

        # You can hookup backtrader to any indicator that runs in MT5
        # Startup and retrieve values from the MT5 indicator "Examples/Envelopes"
        self.mt5sma = getMTraderIndicator(
            store,  # MTraderStorestore instance
            self.datas[0],  # Data stream to run the indicator calculations on
            ("val1",),  # Set accessor(s) for the indicator output
            indicator="Examples/Envelopes",  # MT5 inidicator name
            params=[14, 0, 'MODE_SMA'])()  # indicator parameters

        self.sma = btind.SimpleMovingAverage(self.data)

        # Open a chart window in MT5 with the symbol and timeframe provided by the passed data object.
        chart = MTraderChart(data_obj=self.datas[0])

        chart.addline(self.mt[self.datas[0]._name].val1,
                      style={'shortname': 'myIndi', 'color': 'clrBlue'})

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
            print(f'Examples/Envelopes {self.mt5sma.val1[0]}')

    def notify_data(self, data, status, *args, **kwargs):
        dn = data._name
        dt = datetime.now()
        msg = f'Data Status: {data._getstatusname(status)}'
        print(dt, dn, msg)
        if data._getstatusname(status) == 'LIVE':
            self.live_data = True
        else:
            self.live_data = False


cerebro = bt.Cerebro()
store = MTraderStore(host=HOST, debug=True, datatimeout=10)
cerebro.addstrategy(SmaCross, store)

# comment next 2 lines to use backbroker for backtesting with MTraderStore
# broker = store.getbroker(use_positions=True)
# cerebro.setbroker(broker)

start_date = datetime.now() - timedelta(minutes=500)

data = store.getdata(
    dataname='EURUSD',
    timeframe=bt.TimeFrame.Ticks,
    fromdate=start_date,
    # useask=True,  # ask price instead if the default bid price
    # historical=True
)

cerebro.resampledata(data,
                     timeframe=bt.TimeFrame.Minutes,
                     compression=1
                     )

cerebro.run(stdstats=False)
