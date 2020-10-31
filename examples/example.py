import pytz
import backtrader as bt
import backtrader.indicators as btind
from backtradermql5.mt5store import MTraderStore
from backtradermql5.mt5indicator import getMTraderIndicator
from backtradermql5.mt5chart import MTraderChart, ChartSubWindow
from datetime import datetime, timedelta


class SmaCross(bt.SignalStrategy):
    def __init__(self, store):
        self.buy_order = None
        self.live_data = False

        self.bbM15 = btind.BollingerBands(self.datas[0])
        self.bbM30 = btind.BollingerBands(self.datas[1])

        self.smaM15 = btind.MovingAverageSimple(self.datas[0].close)
        self.smaM30 = btind.MovingAverageSimple(self.datas[1].close)

        # Open a new chart window in MT5 with symbol and timeframe provided by the passed data stream object.
        # Important: instantiate a new chart with class MTraderChart only after you attached any
        # backtrader indicator you want to plot by calling getMTraderIndicator as shown on line 17 above. Otherwise it will fail!

        # Plot the backtrader BollingerBand  and SMA indicator to a chart window with time frame 15 in MT5.

        # Instantiate a new chart window
        chartM15 = MTraderChart(self.datas[0])

        # Instantiate new sub-window. Parameter idx=0 specifies the main window.
        win0 = ChartSubWindow(idx=0, shortname="Bollinger Bands")

        # Add a line buffer to the sub-window
        win0.addline(
            self.bbM15.top, style={"linelabel": "Top", "color": "clrBlue",},
        )
        win0.addline(
            self.bbM15.mid, style={"linelabel": "Middle", "color": "clrYellow",},
        )
        win0.addline(
            self.bbM15.bot, style={"linelabel": "Bottom", "color": "clrGreen",},
        )
        # Add sub-subwindow to chart and draw the line buffers.
        chartM15.addsubwindow(win0)

        # Instantiate second sub-window.
        win1 = ChartSubWindow(idx=1, shortname="Simple Moving Average")
        win1.addline(
            self.smaM15.sma, style={"linelabel": "SMA", "color": "clrBlue", "linestyle": "STYLE_DASH", "linewidth": 2},
        )
        chartM15.addsubwindow(win1)

        # Plot the backtrader BollingerBand  and SMA indicator to a chart window with time frame 30 in MT5.
        chartM30 = MTraderChart(self.datas[1])
        win0 = ChartSubWindow(idx=0, shortname="Bollinger Bands")
        win0.addline(
            self.bbM30.top, style={"linelabel": "Top", "color": "clrBlue",},
        )
        win0.addline(
            self.bbM30.mid, style={"linelabel": "Middle", "color": "clrYellow",},
        )
        win0.addline(
            self.bbM30.bot, style={"linelabel": "Bottom", "color": "clrGreen",},
        )
        chartM30.addsubwindow(win0)
        win1 = ChartSubWindow(idx=1, shortname="Simple Moving Average")
        win1.addline(
            self.smaM30.sma, style={"linelabel": "SMA", "color": "clrBlue", "linestyle": "STYLE_DASH", "linewidth": 2},
        )
        chartM30.addsubwindow(win1)

        # Attach and retrieve values from the MT5 indicator "Examples/MACD"
        self.mt5cma = getMTraderIndicator(
            # MTraderStorestore instance
            store,
            # Data stream to run the indicator calculations on
            self.datas[0],
            # Set accessor(s) for the indicator output lines
            ("cma",),
            # MT5 inidicator name
            indicator="Examples/Custom Moving Average",
            # Indicator parameters.
            # Any omitted values will use the defaults as defind by the indicator
            params=[13, 0, "MODE_SMMA"],
            # The parameter "params" must exit. If you want to use the indicator defaults, pass an empty list
            # params=[],
        )()

    def next(self):
        if self.buy_order is None:
            self.buy_order = self.buy_bracket(limitprice=1.13, stopprice=1.10, size=0.1, exectype=bt.Order.Market)

        if self.live_data:
            cash = self.broker.getcash()

            # Cancel order
            if self.buy_order is not None:
                self.cancel(self.buy_order[0])

        else:
            # Avoid checking the balance during a backfill. Otherwise, it will
            # Slow things down.
            cash = "NA"

        for data in self.datas:
            print(
                f"{data.datetime.datetime()} - {data._name} | Cash {cash} | O: {data.open[0]} H: {data.high[0]} L: {data.low[0]} C: {data.close[0]} V:{data.volume[0]}"
            )
            print(f"MT5 indicator Examples/Custom Moving Average: {self.mt5cma.cma[0]}")  # " {self.mt5macd.macd[0]}")

    def notify_data(self, data, status, *args, **kwargs):
        dn = data._name
        dt = datetime.now()
        msg = f"Data Status: {data._getstatusname(status)}"
        print(dt, dn, msg)
        if data._getstatusname(status) == "LIVE":
            self.live_data = True
        else:
            self.live_data = False


cerebro = bt.Cerebro()
store = MTraderStore(host="192.168.56.124", debug=False, datatimeout=10)
cerebro.addstrategy(SmaCross, store)

# uncomment next 2 lines to use backbroker for live trading with MTraderStore
# broker = store.getbroker(use_positions=True)
# cerebro.setbroker(broker)

start_date = datetime.now() - timedelta(days=5)

data0 = store.getdata(
    dataname="EURUSD",
    timeframe=bt.TimeFrame.Minutes,
    fromdate=start_date,
    compression=15,
    # You need to provide the correct time zone for drawing indicators to charts widows in MT5 to work properly
    tz=pytz.timezone("Europe/Berlin"),
    # useask=True, # Ask price instead if the default bid price
    # addspread=True, # Add the spread value
    historical=True,
)
data1 = store.getdata(
    dataname="EURUSD",
    timeframe=bt.TimeFrame.Minutes,
    fromdate=start_date,
    compression=30,
    # You need to provide the correct time zone for drawing indicators to charts widows in MT5 to work properly
    tz=pytz.timezone("Europe/Berlin"),
    # useask=True, # Ask price instead if the default bid price
    # addspread=True, # Add the spread value
    historical=True,
)

cerebro.adddata(data0)
cerebro.adddata(data1)

cerebro.run(stdstats=False)
