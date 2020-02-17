from backtrader import bt

import uuid


def getMTraderIndicator(mtstore, data_obj, lines=list(), *args, **kwargs):

    globals()["lines"] = lines
    globals()["params"] = kwargs

    def setAttributes():
        setattr(MTraderIndicator, "mtstore", mtstore)
        setattr(MTraderIndicator, "data_obj", data_obj)

    class MTraderIndicator(bt.Indicator):

        lines = lines
        params = params

        def __init__(self):

            self.p.timeframe = self.data_obj._timeframe
            self.p.compression = self.data_obj._compression
            self.p.indicator = self.p.indicator
            self.p.params = self.p.params
            self.p.id = str(uuid.uuid4())
            self.p.symbol = self.data_obj._name
            self.p.linecount = len(lines)
            ret_val = self.mtstore.config_indicator(
                self.p.symbol,
                self.p.timeframe,
                self.p.compression,
                self.p.indicator,
                self.p.id,
                self.p.params,
                self.p.linecount,
            )

            self.p.indicatorId = ret_val["id"]

        def next(self):
            fromDate = int(self.data_obj.datetime.datetime().timestamp())

            ret_val = self.mtstore.indicator(self.p.indicatorId, fromDate)

            # TODO error handling
            i = 0
            for d in ret_val["data"]:
                self.lines[i][0] = float(ret_val["data"][i])
                i += 1

    setAttributes()

    return MTraderIndicator
