# Metaquotes MQL5 - JSON - API

### Development state: stable beta (code is stable)

## Table of Contents
* [About the Project](#about-the-project)
* [Installation](#installation)
* [Documentation](#documentation)
* [Usage](#usage)
* [Live data and streaming events](#live-data-and-streaming-events)
* [License](#license)

## About the Project

This project was developed to work as a server for the Backtrader Python trading framework. It is based on ZeroMQ sockets and uses JSON format to communicate. But now it has grown to the independent project. You can use it with any language that has [ZeroMQ binding](http://zeromq.org/bindings:_start).


Backtrader Python client located here: [Python Backtrader - Metaquotes MQL5 ](https://github.com/khramkov/Backtrader-MQL5-API)

In development:
* Add error handling to docs
* Trades info
* Experation
* Devitation
* Netting/hedging mode switch
* Stop limit orders

## Installation

1. Install ZeroMQ for MQL5 [https://github.com/dingmaotu/mql-zmq](https://github.com/dingmaotu/mql-zmq)
2. Put `include/Json.mqh` from this repo to your MetaEditor `include` directoty.
3. Download and compile `experts/JsonAPI.mq5` script. 
4. Check if Metatrader 5 automatic trading is allowed.
5. Attach the script to a chart in Metatrader 5.
6. Allow DLL import in dialog window.
7. Check if the ports are free to use. (default:`15555`,`15556`, `15557`,`15558`)

Tested on macOS Mojave / Windows 10 in Parallels Desktop container.

## Documentation

The script uses four ZeroMQ sockets:

1. `System socket` - recives requests from client and replies 'OK'
2. `Data socket` - pushes data to client depending on the request via System socket.
3. `Live socket` - automatically pushes last candle when it closes.
4. `Streaming socket` - automatically pushes last transaction info every time it happens.

The idea is to send requests via `System socket` and recieve results/errors via `Data socket`. Event handlers should be created for `Live socket` and `Streaming socket` because the server sends data to theese sockets automatically. See examples in [Live data and streaming events](#live-data-and-streaming-events) section.

`System socket` request uses default JSON dictionary:

```
{
	"action": None,
	"actionType": None,
	"symbol": None,
	"chartTF": None,
	"fromDate": None,
	"toDate": None,
	"id": None,
	"magic": None,
	"volume": None,
	"price": None,
	"stoploss": None,
	"takeprofit": None,
	"expiration": None,
	"deviation": None,
	"comment": None
}
```
Check out the available combinations of `action` and `actionType`:

action     | actionType           | Description                |
-----------|----------------------|----------------------------|
CONFIG     | None            	    | Set script configuration   |
ACCOUNT    | None                 | Get account settings       |
BALANCE    | None                 | Get current balance        |
POSITIONS  | None                 | Get current open positions |
ORDERS     | None                 | Get current open orders    |
HISTORY    | DATA                 | Get data history           |
HISTORY    | TRADES               | Get trades history         |
TRADE      | ORDER_TYPE_BUY       | Buy market                 |
TRADE      | ORDER_TYPE_SELL      | Sell market                |
TRADE      | ORDER_TYPE_BUY_LIMIT | Buy limit                  |
TRADE      | ORDER_TYPE_SELL_LIMIT| Sell limit                 |
TRADE      | ORDER_TYPE_BUY_STOP  | Buy stop                   |
TRADE      | ORDER_TYPE_SELL_STOP | Sell stop                  |
TRADE      | POSITION_MODIFY      | Position modify            |
TRADE      | POSITION_PARTIAL     | Position close partial     |
TRADE      | POSITION_CLOSE_ID    | Position close by id       |
TRADE      | POSITION_CLOSE_SYMBOL| Positions close by symbol  |
TRADE      | ORDER_MODIFY         | Order modify               |
TRADE      | ORDER_CANCEL         | Order cancel               |

Python 3 API class example:

``` python
import zmq

class MTraderAPI:
    def __init__(self, host=None):
        self.HOST = host or 'localhost'
        self.SYS_PORT = 15555       # REP/REQ port
        self.DATA_PORT = 15556      # PUSH/PULL port
        self.LIVE_PORT = 15557      # PUSH/PULL port
        self.EVENTS_PORT = 15558    # PUSH/PULL port

        # ZeroMQ timeout in seconds
        sys_timeout = 1
        data_timeout = 10

        # initialise ZMQ context
        context = zmq.Context()

        # connect to server sockets
        try:
            self.sys_socket = context.socket(zmq.REQ)
            # set port timeout
            self.sys_socket.RCVTIMEO = sys_timeout * 1000
            self.sys_socket.connect('tcp://{}:{}'.format(self.HOST, self.SYS_PORT))

            self.data_socket = context.socket(zmq.PULL)
            # set port timeout
            self.data_socket.RCVTIMEO = data_timeout * 1000
            self.data_socket.connect('tcp://{}:{}'.format(self.HOST, self.DATA_PORT))
        except zmq.ZMQError:
            raise zmq.ZMQBindError("Binding ports ERROR")

    def _send_request(self, data: dict) -> None:
        """Send request to server via ZeroMQ System socket"""
        try:
            self.sys_socket.send_json(data)
            msg = self.sys_socket.recv_string()
            # terminal received the request
            assert msg == 'OK', 'Something wrong on server side'
        except AssertionError as err:
            raise zmq.NotDone(err)
        except zmq.ZMQError:
            raise zmq.NotDone("Sending request ERROR")

    def _pull_reply(self):
        """Get reply from server via Data socket with timeout"""
        try:
            msg = self.data_socket.recv_json()
        except zmq.ZMQError:
            raise zmq.NotDone('Data socket timeout ERROR')
        return msg

    def live_socket(self, context=None):
        """Connect to socket in a ZMQ context"""
        try:
            context = context or zmq.Context.instance()
            socket = context.socket(zmq.PULL)
            socket.connect('tcp://{}:{}'.format(self.HOST, self.LIVE_PORT))
        except zmq.ZMQError:
            raise zmq.ZMQBindError("Live port connection ERROR")
        return socket

    def streaming_socket(self, context=None):
        """Connect to socket in a ZMQ context"""
        try:
            context = context or zmq.Context.instance()
            socket = context.socket(zmq.PULL)
            socket.connect('tcp://{}:{}'.format(self.HOST, self.EVENTS_PORT))
        except zmq.ZMQError:
            raise zmq.ZMQBindError("Data port connection ERROR")
        return socket

    def construct_and_send(self, **kwargs) -> dict:
        """Construct a request dictionary from default and send it to server"""

        # default dictionary
        request = {
            "action": None,
            "actionType": None,
            "symbol": None,
            "chartTF": None,
            "fromDate": None,
            "toDate": None,
            "id": None,
            "magic": None,
            "volume": None,
            "price": None,
            "stoploss": None,
            "takeprofit": None,
            "expiration": None,
            "deviation": None,
            "comment": None
        }

        # update dict values if exist
        for key, value in kwargs.items():
            if key in request:
                request[key] = value
            else:
                raise KeyError('Unknown key in **kwargs ERROR')

        # send dict to server
        self._send_request(request)

        # return server reply
        return self._pull_reply()
```
## Usage
All examples will be on Python 3. Lets create an instance of MetaTrader API class:

``` python
api = MTraderAPI()
```

First of all we should configure script `symbol` and `timeframe`. Live data stream will be configured to the seme params.

``` python
rep = api.construct_and_send(action="CONFIG", symbol="EURUSD", chartTF="M5")
print(rep)
```

Get information about trading account.

``` python
rep = api.construct_and_send(action="ACCOUNT")
print(rep)
```

Get historical data. `fromDate` should be in timestamp format. The data will be loadet to the last candle if `toDate` is `None`. Notice, that the script sends the last unclosed candle too. You should delete it manually.

There are some issues:

- MetaTrader keeps historical data in cache. But when you make a request for the first time, MetaTrader downloads data from a broker. This operation can exceed `Data socket` timeout. It depends on your broker. Second request will be handeled quickly.
- It takes 6-7 seconds to process `50000` M1 candles. It was tested on Windows 10 in Parallels Desktop container with 4 cores and 4GB RAM. So if you need more data there are three ways to handle it. 1) Increase `Data socket` timeout. 2) You can load data partially using `fromDate` and `toDate`. 3) You can use more powerfull hardware.

``` python
rep = api.construct_and_send(action="HISTORY", actionType="DATA", symbol="EURUSD", chartTF="M5", fromDate=1555555555)
print(rep)
```

History data reply example:

```
{'data': [[1560782340, 1.12271, 1.12288, 1.12269, 1.12277, 46.0],[1560782400, 1.12278, 1.12299, 1.12276, 1.12297, 43.0],[1560782460, 1.12296, 1.12302, 1.12293, 1.123, 23.0]]}
```

Buy market order.

``` python
rep = api.construct_and_send(action="TRADE", actionType="ORDER_TYPE_BUY", symbol="EURUSD", "volume": 0.1, "stoploss": 1.1, "takeprofit": 1.3)
print(rep)
```

Sell limit order. Remember to switch SL/TP depending on BUY/SELL, or you will get `invalid stops` error.

- BUY:  	SL < price < TP
- SELL: 	SL > price > TP

``` python
rep = api.construct_and_send(action="TRADE", actionType="ORDER_TYPE_SELL_LIMIT", symbol="EURUSD", "volume": 0.1, "price": 1.2, "stoploss": 1.3, "takeprofit": 1.1)
print(rep)
```
## Live data and streaming events

Event handler example for `Live socket` and `Data socket`.
 
``` python
import zmq
import threading

api = MTraderAPI()


def _t_livedata():
    socket = api.live_socket()
    while True:
        try:
            last_candle = socket.recv_json()
        except zmq.ZMQError:
            raise zmq.NotDone("Live data ERROR")
        print(last_candle)


def _t_streaming_events():
    socket = api.streaming_socket()
    while True:
        try:
            trans = socket.recv_json()
            request, reply = trans.values()
        except zmq.ZMQError:
            raise zmq.NotDone("Streaming data ERROR")
        print(request)
        print(reply)


for _ in range(3):
    t = threading.Thread(target=_t_livedata, daemon=True)
    t.start()

for _ in range(3):
    t = threading.Thread(target=_t_streaming_events, daemon=True)
    t.start()

while True:
    pass
```


There are only two variants of `Live socket` data. When everything is ok, the script sends candle data on close:

```
{"status":"CONNECTED","data":[1560780120,1.12186,1.12194,1.12186,1.12191,15.00000]}
```

If the terminal has lost connection to the market:

```
{"status":"DISCONNECTED"}
```

When the terminal reconnects to the market, it sends the last closed candle again. So you should update the historical data. Make the `action="HISTORY"` request with `fromDate` equal to your last candle timestamp.

`OnTradeTransaction` function is called when the trade transaction event occurs. `Streaming socket` sends `TRADE_TRANSACTION_REQUEST` data every time it happens. Try to create and modify orders in the MQL5 terminal manually and check the expert logging tab for better understanding. Also see [MQL5 docs](https://www.mql5.com/en/docs/event_handlers/ontradetransaction). 

`TRADE_TRANSACTION_REQUEST` request data:

```
{
	'action': 'TRADE_ACTION_DEAL', 
	'order': 501700843, 
	'symbol': 'EURUSD', 
	'volume': 0.1, 
	'price': 1.12181, 
	'stoplimit': 0.0, 
	'sl': 1.1, 
	'tp': 1.13, 
	'deviation': 10, 
	'type': 'ORDER_TYPE_BUY', 
	'type_filling': 'ORDER_FILLING_FOK', 
	'type_time': 'ORDER_TIME_GTC', 
	'expiration': 0, 
	'comment': None, 
	'position': 0, 
	'position_by': 0
}
```
`TRADE_TRANSACTION_REQUEST` result data:

```
{
	'retcode': 10009, 
	'result': 'TRADE_RETCODE_DONE', 
	'deal': 501700843, 
	'order': 501700843, 
	'volume': 0.1, 
	'price': 1.12181, 
	'comment': None, 
	'request_id': 8, 
	'retcode_external': 0
}
```

## License
This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See `LICENSE` for more information.
