from backtrader import bt
import math
import uuid


class MTraderChart(bt.Indicator):

    # Inherited Indicator class requires at least one line
    lines = ("dummyline",)
    params = (("data_obj", None),)

    line_store = list()
    # TODO implent drawing of chart objects
    # graphic_types = ["curve", "line", "arrowbuy", "arrowsell"]

    def __init__(self):
        self.last_date = 0
        self.p.chartId = str(uuid.uuid4())
        self.p.symbol = self.p.data_obj._name
        self.p.timeframe = self.p.data_obj._timeframe
        self.p.compression = self.p.data_obj._compression
        self.p.store = self.p.data_obj.o

        self.p.store.config_chart(
            self.p.chartId, self.p.symbol, self.p.timeframe, self.p.compression,
        )

    def next(self):
        state = self.p.data_obj._state
        qsize = self.p.data_obj._historyback_queue_size
        _ST_LIVE = self.p.data_obj._ST_LIVE

        for obj in self.line_store:
            date = self.p.data_obj.datetime.datetime()
            value = obj["line"][0]
            if date != self.last_date and not math.isnan(value):
                obj["values"].append(value)
                # Push historical indicator values when all historical price data has been processed
                if qsize <= 1 or state == _ST_LIVE:
                    self.p.store.push_chart_data(
                        self.p.chartId, obj["chartIndicatorId"], obj["values"]
                    )
                    obj["values"] = []
                self.last_date = date

    def addobject(self):
        pass

    def addline(self, line, *args, **kwargs):

        style = {
            "shortname": "JsonAPI",
            "color": "clrBlue",
            "linetype": "DRAW_LINE",
            "linestyle": "STYLE_SOLID",
            "linewidth": 1,
        }
        style.update(**kwargs["style"])

        chartIndicatorId = str(uuid.uuid4())
        chartIndicatorSubWindow = 1
        self.line_store.append(
            {
                "line": line,
                "chartIndicatorId": chartIndicatorId,
                "chartIndicatorSubWindow": chartIndicatorSubWindow,
                "style": style,
                "values": [],
            }
        )
        self.p.store.chart_add_indicator(
            self.p.chartId, chartIndicatorId, chartIndicatorSubWindow, style
        )
