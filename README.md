# Python Backtrader - Metaquotes MQL5 - API

### Development state: first stable release.

Working in production on Debian 10.

## Table of Contents

- [About the Project](#about-the-project)
- [Installation](#installation)
- [Documentation](#documentation)
- [Usage](#usage)
- [License](#license)

## About the Project

This is the Backtrader part of the project. MQL5 side of this project is located here: [MQL5 - JSON - API](https://github.com/khramkov/MQL5-JSON-API)

In development:

- Upload data on reconnect

## Installation

1. `pip install backtrader`
2. `pip install pyzmq`
3. Check if the ports are free to use. (default:`15555`,`15556`, `15557`,`15558`)

## Documentation

See [MQL5 - JSON - API documentation](https://github.com/khramkov/MQL5-JSON-API) for better understanding.

You can create market or pending order with the default `backtrader` command.

```python
self.buy_order = self.buy(size=0.1, price=1.11, exectype=bt.Order.Limit)
```

If you want to cancel it.

```python
self.cancel(self.buy_order)
```

When you use `bracket` orders, one order with stops will be created on the MQL5 side.

```python
self.buy_order = self.buy_bracket(limitprice=1.13, stopprice=1.10, size=0.1, exectype=bt.Order.Market)
```

If you want to cancel `bracket` orders, you shold cancel only the first one.

```python
self.cancel(self.buy_order[0])
```

## Usage

### Live trading example

```python
import backtrader as bt
from backtradermt5.mt5store import MTraderStore
from datetime import datetime, timedelta


class SmaCross(bt.SignalStrategy):

    def __init__(self):
        self.buy_order = None
        self.live_data = False

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
            cash = 'NA'

        for data in self.datas:
            print(f'{data.datetime.datetime()} - {data._name} | Cash {cash} | O: {data.open[0]} H: {data.high[0]} L: {data.low[0]} C: {data.close[0]} V:{data.volume[0]}')

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

# comment next 2 lines to use backbroker for backtesting with MTraderStore
broker = store.getbroker(use_positions=True)
cerebro.setbroker(broker)

start_date = datetime.now() - timedelta(minutes=500)

data = store.getdata(dataname='EURUSD', timeframe=bt.TimeFrame.Ticks,
                     fromdate=start_date) #, useask=True, historical=True)
                     # the parameter "useask" will request the ask price insetad if the default bid price

cerebro.resampledata(data,
                     timeframe=bt.TimeFrame.Seconds,
                     compression=30
                     )

cerebro.run(stdstats=False)
cerebro.plot(style='candlestick', volume=False)
```

### Download CSV data

You can instruct MT5 to download historical data as a CSV file. Files will be saved into the local Metatrader 5 Terminal installation folder:

`[MT5 Terminal]/MQL/Files/Data`

The example below downloads data for the past 6 months as tick data.

```python
from datetime import datetime, timedelta
from backtradermql5.mt5store import MTraderStore
import backtrader as bt

store = MTraderStore(host='192.168.1.20') # Metatrader 5 running on a diffenet host

start_date = datetime.now() - timedelta(months=6)

cerebro = bt.Cerebro()
data2 = store.getdata(dataname='EURUSD',
                      timeframe=bt.TimeFrame.Ticks,
                      fromdate=start_date
                      )

cerebro.run(stdstats=False)
```

### Using MT5 Indicators and plotting to MT5 charts

#### MT5 Indicators

You can use any MT5 indicator directly from Backtrader via the `MTraderIndicator` class.

```
    def __init__(self, store):
        self.mt5macd = getMTraderIndicator(
            # MTraderStorestore instance
            store,
            # Data feed to run the indicator calculations on
            self.datas[0],
            # Set accessor(s) for the indicator output
            ("macd", "signal",),
            # MT5 inidicator name
            indicator="Examples/MACD",
            # Indicator parameters.
            # Any omitted values will use the defaults as defind by the indicator
            params=[12, 26, 9, "PRICE_CLOSE"],
        )()

    def next(self):
        print(f"MT5 indicator Examples/MACD: {self.mt5macd.signal[0]} {self.mt5macd.macd[0]}")
```

For a fully working and commented example of a Strategy refer to `example.py`.

#### Plotting indicators to MT5 charts

You can open and draw directly to a chart in MT5 via the `MTraderChart` class.

```
    def __init__(self, store):
        self.bb = btind.BollingerBands(self.data)
        chart = MTraderChart(data_obj=self.datas[0])
        indi0 = ChartIndicator(idx=0, shortname="Bollinger Bands")
        chart.addline(self.bb.top, style={
                    "linelabel": "Top", "color": "clrBlue"})
        chart.addindicator(indi0)
```

For a fully working and commented example of a Strategy refer to `example.py`.

## License

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See `LICENSE` for more information.

```

```
