from backtrader import bt
import math
import uuid


class MTraderChart(bt.Indicator):

    # Inherited Indicator class requires at least one line
    lines = ("dummyline",)

    def __init__(self):
        """
        Opens a chart window in MT5 withe the smybol and timeframe of the passed data stream object.
        """
        self.windows = list()
        self.window_count = 0
        # TODO implent drawing of chart objects
        # graphic_types = ["curve", "line", "arrowbuy", "arrowsell"]
        self.p.chartId = str(uuid.uuid4())
        self.p.symbol = self.data._name
        self.p.timeframe = self.data._timeframe
        self.p.compression = self.data._compression
        self.p.store = self.data.o

        self.p.store.config_chart(self.p.chartId, self.p.symbol, self.p.timeframe, self.p.compression)

    def next(self):
        state = self.data._state
        qsize = self.data._historyback_queue_size
        _ST_LIVE = self.data._ST_LIVE

        for window in self.windows:
            for line in window.line_store:
                # # Support for repainting indicators
                # # Wait for first indicator calculation
                # mp = obj["line"]._minperiod
                # if obj["line"].lencount > 0:

                date = self.data.datetime.datetime()
                value = line["line"][0]
                if date != line["last_date"] and not math.isnan(value):
                    line["values"].append(value)
                    # Push historical indicator values when all historical price data has been processed
                    if qsize <= 1 or state == _ST_LIVE:
                        # # Support for repainting indicators
                        # if obj["repaint"] is True and obj["line"].lencount >= mp:
                        #     obj["values"] = obj["values"][: len(obj["values"]) - mp]
                        #     for i in reversed(range(0, mp)):
                        #         obj["values"].append(obj["line"][i * -1])
                        self.p.store.push_chart_data(
                            self.p.chartId, window.windowId, line["bufferId"], line["values"],
                        )
                        line["values"] = []
                    line["last_date"] = date

    def addsubwindow(self, window):
        """
        Adds an indicator instance to a chart subwindow in MT5.
        """
        if window.windowIdx > self.window_count:
            self.window_count += 1
            window.windowIdx = self.window_count

        window.windowId = str(uuid.uuid4())

        self.p.store.chart_add_indicator(self.p.chartId, window.windowId, window.windowIdx, window.shortname)
        for line in window.line_store:
            self.p.store.chart_indicator_add_line(self.p.chartId, window.windowId, line["style"])
        self.windows.append(window)


class ChartSubWindow:
    """
    Chart subwindow class
    """

    def __init__(self, idx, shortname):
        self.windowIdx = idx
        self.shortname = shortname
        self.windowId = None
        self.indicator_line_count = -1
        self.line_store = []

    def addline(self, line, *args, **kwargs):
        style = {
            "linelabel": "Value",
            "color": "clrBlue",
            "linetype": "DRAW_LINE",
            "linestyle": "STYLE_SOLID",
            "linewidth": 1,
        }
        style.update(**kwargs["style"])

        self.indicator_line_count += 1

        self.line_store.append(
            {
                "last_date": 0,
                "line": line,
                "style": style,
                "values": [],
                "bufferId": self.indicator_line_count
                # "repaint": False,
            }
        )
