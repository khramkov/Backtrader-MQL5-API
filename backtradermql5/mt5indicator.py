# from backtrader.indicators import Indicator
import backtrader as bt
from backtrader import date2num, num2date
import uuid


class MTraderIndicator(bt.Indicator):
    lines = (
        "val1",
        "val2",
        "val3",
        "val4",
        "val5",
        "val6",
        "val7",
        "val8",
        "val9",
        "val10",
    )
    params = dict(indicator="", params=[],)  # movav=btind.MovAv.Simple

    def __init__(self):
        # self.addminperiod(self.params.period)
        # self.store = self.data._store

        self.timeframe = self.data._timeframe
        self.compression = self.data._compression
        self.indicator = self.p.indicator
        self.indicatorParams = self.p.params
        self.id = str(uuid.uuid4())
        self.symbol = self.data._name
        # print(self.data.open[0])
        # self.lines.val = 1.0

    def nextstart(self):
        print("------------Setup and configure MT5 indicator here")
        self.store = self.data.o
        fromDate = str(self.data.datetime.datetime())  # .timestamp()
        self.store.config_indicator(
            fromDate,
            self.symbol,
            self.timeframe,
            self.compression,
            self.indicator,
            self.id,
            self.indicatorParams,
        )
        self.indicatorId = 1.0
        self.lines.val1[0] = 1.0

    def nextX(self):
        timestamp = self.data.datetime.datetime().timestamp()
        print(timestamp)
        # print(self.timeframe, self.compression)
        # periodData = []
        # a = [
        #     num2date(x).timestamp()
        #     for x in self.data.datetime.get(size=self.p.period).tolist()
        # ]
        # periodData.append(a)
        # periodData.append(self.data.datetime.get(size=self.p.period).tolist())
        # periodData.append(self.data.open.get(size=self.p.period).tolist())
        # periodData.append(self.data.high.get(size=self.p.period).tolist())
        # periodData.append(self.data.low.get(size=self.p.period).tolist())
        # periodData.append(self.data.close.get(size=self.p.period).tolist())
        # print(num2date(periodData[0][1]).timestamp())
        # print(self.data.datetime.datetime())
        # for a in periodData:
        #     print("a", a)

        self.store.indicator(self.indicatorId, timestamp)

        self.lines.val1[0] = 1.0

