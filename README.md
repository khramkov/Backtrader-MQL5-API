# Python Backtrader - Metaquotes MQL5 - API

### Development state: stable beta (code is stable)

## Table of Contents
* [About the Project](#about-the-project)
* [Installation](#installation)
* [Documentation](#documentation)
* [Usage](#usage)
* [License](#license)

## About the Project

This is Backtrader part of the project. MQL5 side of this project located here: [Metaquotes MQL5 - Python Backtrader - API.](https://github.com/khramkov/MQL5-JSON-API)

Only Market orders are working!!!

In development:

* Pending orders
* Docs
* Upload data on reconnect

## Installation

1. `pip install pyzmq`
2. Check if the ports are free to use. (default:`15555`,`15556`, `15557`,`15558`)

Tested on macOS Mojave / Windows 10 in Parallels Desktop container.

## Documentation

See [Metaquotes MQL5 - Python Backtrader - API](https://github.com/khramkov/MQL5-JSON-API) documentation for understanding the logic.

## Usage

 
``` python
import backtrader as bt
from mt5.mt5store import MTraderStore
from datetime import datetime, timedelta


class SmaCross(bt.SignalStrategy):
    params = (

        ('take_profit', 0.04),
        ('stop_loss', 0.01),

    )
    def __init__(self):

        self.buy_order = None
        self.live_data = False

    def next(self):
        if self.buy_order is None:
            self.buy_order = self.buy(size=0.1, exectype=bt.Order.Market)
            # self.buy_order = self.buy_bracket(limitprice=1.13, stopprice=1.10, size=0.1, exectype=bt.Order.Market)
            # pass


        if self.live_data:
            cash = self.broker.getcash()
				
			# Cancel order 
			# if self.buy_order is not None:
			# 	self.cancel(self.buy_order[0])

        else:
            # Avoid checking the balance during a backfill. Otherwise, it will
            # Slow things down.
            cash = 'NA'

        for data in self.datas:
            print(f'{data.datetime.datetime()} - {data._name} | Cash {cash} | O: {data.open[0]} H: {data.high[0]} L: {data.low[0]} C: {data.close[0]} V:{data.volume[0]} SMA:{self.sma[0]}')

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
cerebro.addstrategy(SmaCross)

store = MTraderStore()

broker = store.getbroker(use_positions=True)
cerebro.setbroker(broker)

start_date = datetime.now() - timedelta(minutes=500)

data = store.getdata(dataname='EURUSD', timeframe=bt.TimeFrame.Minutes,
                     fromdate=start_date, compression=1) #, historical=True)

cerebro.adddata(data)
cerebro.run(stdstats=False)
cerebro.plot(style='candlestick', volume=False)
```

## License
This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See `LICENSE` for more information.
