#!/usr/bin/env python
# encoding: utf-8
import os
import time

from dotenv import load_dotenv

from context import BackTestContext, BackTestKLineCached
from enumeration import KLineSymbol, KLineInterval
from strategies import IStrategy

load_dotenv()
kline_provider = os.environ.get("KLINE_PROVIDER")

kline_symbol = KLineSymbol.LtcUsdt
kline_interval = KLineInterval.OneMinute

start_ts = int(time.time()) - 86400 * 100

context = BackTestContext(kline_provider, kline_symbol, kline_interval, start_ts)
kline_cached = BackTestKLineCached(context)
strategy = IStrategy(context)

from_ts = start_ts
while True:
    kline = kline_cached.get_next_kline()
    if kline is None:
        break

    strategy.run(kline)
