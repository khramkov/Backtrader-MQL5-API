from backtrader import bt
import math
import uuid


class MTraderChart(bt.Indicator):

    # Inherited Indicator class requires at least one line
    lines = ("dummyline",)
    # params = (("data_obj", None),)

    # Do not define any class attributes here. All MTraderChart would share the same attribute.
    # This is probably because of the class inheritance of bt.indicator?

    def __init__(self):
        """
        Opens a chart window in MT5 withe the smybol and timeframe of the passed data stream object.
        """
        self.line_store = list()
        self.indicator_buffers = dict()
        self.subwindow_count = 0
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

        for obj in self.line_store:
            # # Support for repainting indicators
            # # Wait for first indicator calculation
            # mp = obj["line"]._minperiod
            # if obj["line"].lencount > 0:

            date = self.data.datetime.datetime()
            value = obj["line"][0]
            if date != obj["last_date"] and not math.isnan(value):
                obj["values"].append(value)
                # Push historical indicator values when all historical price data has been processed
                if qsize <= 1 or state == _ST_LIVE:
                    # # Support for repainting indicators
                    # if obj["repaint"] is True and obj["line"].lencount >= mp:
                    #     obj["values"] = obj["values"][: len(obj["values"]) - mp]
                    #     for i in reversed(range(0, mp)):
                    #         obj["values"].append(obj["line"][i * -1])
                    self.p.store.push_chart_data(
                        self.p.chartId, obj["chartIndicatorId"], obj["bufferId"], obj["values"],
                    )
                    obj["values"] = []
                obj["last_date"] = date

    def addindicator(self, window=0, shortname="JsonAPIIndiatorSH"):
        """
        Adds an indicator instance in MT5.
        """
        if window > self.subwindow_count:
            self.subwindow_count += 1
            window = self.subwindow_count

        chartIndicatorId = str(uuid.uuid4())

        self.p.store.chart_add_indicator(self.p.chartId, chartIndicatorId, window, shortname)
        self.indicator_buffers[chartIndicatorId] = 0
        return chartIndicatorId

    def addbuffer(self, line, *args, **kwargs):
        style = {
            "linelabel": "Value",
            "color": "clrBlue",
            "linetype": "DRAW_LINE",
            "linestyle": "STYLE_SOLID",
            "linewidth": 1,
        }
        style.update(**kwargs["style"])
        chartIndicatorId = kwargs["indicator"]
        self.line_store.append(
            {
                "last_date": 0,
                "line": line,
                "chartIndicatorId": chartIndicatorId,
                "style": style,
                "values": [],
                "bufferId": self.indicator_buffers[chartIndicatorId],
                # "repaint": False,
            }
        )
        self.p.store.chart_indicator_add_buffer(self.p.chartId, chartIndicatorId, style)
        self.indicator_buffers[chartIndicatorId] += 1

