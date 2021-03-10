from backtrader import bt
import uuid


def getMTraderIndicator(mtstore, data_obj, lines=list(), plotinfo=dict(), plotlines=dict(), *args, **kwargs):

    if "plotname" not in plotinfo:
        plotinfo["plotname"] = kwargs["indicator"]
    globals()["plotinfo"] = plotinfo
    globals()["plotlines"] = plotlines
    globals()["lines"] = lines
    globals()["params"] = kwargs

    def setAttributes():
        setattr(MTraderIndicator, "mtstore", mtstore)
        setattr(MTraderIndicator, "data_obj", data_obj)

    class MTraderIndicator(bt.Indicator):

        lines = lines
        params = params
        plotinfo = plotinfo
        plotlines = plotlines

        def __init__(self):
            self.last_fromDate = 0
            self.p.timeframe = self.data_obj._timeframe
            self.p.compression = self.data_obj._compression
            self.p.id = str(uuid.uuid4())
            self.p.symbol = self.data_obj._dataname
            self.p.linecount = len(lines)
            self.p.params = [str(x) for x in self.p.params]

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

            if fromDate != self.last_fromDate:
                ret_val = self.mtstore.indicator_data(self.p.indicatorId, fromDate)
                self.last_fromDate = fromDate

                for i in range(len(ret_val["data"])):
                    self.lines[i][0] = float(ret_val["data"][i])

    setAttributes()

    return MTraderIndicator
