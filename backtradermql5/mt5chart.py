from backtrader import bt

import uuid


class MTraderChart(bt.Indicator):

    lines = ("dummyline",)  # at least one line is required
    params = (("data_obj", None),)

    line_store = dict()
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
        _ST_HISTORBACK = self.p.data_obj._ST_HISTORBACK

        for name, obj in self.line_store.items():

            date = self.p.data_obj.datetime.datetime()
            value = obj["line"][0]

            # if len(obj["values"]) > len(obj["values"]) - 20:
            # if str(date) == "2020-02-21 22:53:00":
            # if state == 2:  # or state == 3:  # or state == 4:

            if date != self.last_date:
                if qsize <= 1 or state == _ST_LIVE:
                    obj["values"].append(value)
                    self.p.store.push_chart_data(
                        self.p.chartId, obj["chartIndicatorId"], obj["values"]
                    )
                    obj["values"] = []
                elif state == _ST_HISTORBACK:
                    # else:
                    obj["values"].append(value)
                self.last_date = date

    def drawarrow(self):
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

        # TODO if not name in line_store ?

        chartIndicatorId = str(uuid.uuid4())
        chartIndicatorSubWindow = 1
        self.line_store[kwargs["name"]] = {
            "line": line,
            "chartIndicatorId": chartIndicatorId,
            "chartIndicatorSubWindow": chartIndicatorSubWindow,
            "style": style,
            "values": [],
        }
        self.p.store.chart_add_indicator(
            self.p.chartId, chartIndicatorId, chartIndicatorSubWindow, style
        )

