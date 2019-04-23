# Python Backtrader - Metaquotes MQL5 - API

### Development state: Alfa (Code not stable yet, documentation in development)

[Report Bug](https://github.com/khramkov/Backtrader-MQL5-API/issues) or [Request Feature](https://github.com/khramkov/Backtrader-MQL5-API
/issues)

## Table of Contents
* [About the Project](#about-the-project)
* [Installation and usage](#installation-and-usage)
* [License](#license)

## About The Project

This project was created to work as a broker for Backtrader trading framework. It uses ZeroMQ sockets to communicate. Python side of this project located here: [Python Backtrader - Metaquotes MQL5 ](https://github.com/khramkov/MQL5-Backtrader-API)

Working:
* Account info
* Balance info
* Historical data
* Live data
* Fetching orders/positions
* Order creation

Not working:
* Cancel order
* Close position
* Trades info
* Check socket connection
* Change timeframe and instrument symdol

## Installation and usage

'''
from exchanges import MT5Store
import backtrader as bt
from datetime import datetime, timedelta


class TestStrategy(bt.Strategy):

    def __init__(self):

        self.sma = bt.indicators.SMA(self.data,period=21)

    def next(self):

        # Get cash and balance
        # New broker method that will let you get the cash and balance for
        # any wallet. It also means we can disable the getcash() and getvalue()
        # rest calls before and after next which slows things down.

        if self.live_data:
            cash, value = self.broker.get_balance()
        else:
            # Avoid checking the balance during a backfill. Otherwise, it will
            # Slow things down.
            cash = 'NA'

        for data in self.datas:

            print(f'{data.datetime.datetime()} - {data._name} | Cash {cash} | O: {data.open[0]} H: {data.high[0]} L: {data.low[0]} C: {data.close[0]} V:{data.volume[0]} SMA:{self.sma[0]}')

    def notify_data(self, data, status, *args, **kwargs):
        dn = data._name
        dt = datetime.now()
        msg= f'Data Status: {data._getstatusname(status)}'
        print(dt,dn,msg)
        if data._getstatusname(status) == 'LIVE':
            self.live_data = True
        else:
            self.live_data = False


cerebro = bt.Cerebro(quicknotify=True)
cerebro.addstrategy(TestStrategy)
store = MT5Store(currency='EURUSD', debug=True)
broker = store.getbroker()
cerebro.setbroker(broker)

hist_start_date = datetime.now() - timedelta(minutes=30)
data = store.getdata(dataname='EURUSD', name='EURUSD',
                         timeframe=bt.TimeFrame.Minutes, fromdate=hist_start_date,
                         compression=1, drop_newest=True) #, historical=True)

cerebro.adddata(data)
cerebro.run()
'''


## License
Distributed under the MIT License. See `LICENSE` for more information.
