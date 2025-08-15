#!/usr/bin/env python
# encoding: utf-8
import os
import time
from _decimal import Decimal

from dotenv import load_dotenv

from context import BackTestContext, BackTestKLineCached
from enumeration import KLineSymbol, KLineInterval
from strategies import IStrategy
from strategies.moving_average_trend import MovingAverageTrendStrategy

load_dotenv()
kline_provider = os.environ.get("KLINE_PROVIDER")

kline_symbol = KLineSymbol.LtcUsdt
kline_interval = KLineInterval.OneMinute

start_ts = int(time.time()) - 86400 * 500

context = BackTestContext(kline_provider, kline_symbol, kline_interval, start_ts)
context.init_currency_balances(Decimal("0"), Decimal("10000"))
context.init_exchange_fee_rate(Decimal("0.002"))
kline_cached = BackTestKLineCached(context)

# strategy = IStrategy(context)
strategy = MovingAverageTrendStrategy(context, 20, 30, Decimal("0.04"), Decimal("0.04"))

from_ts = start_ts
while True:
    kline = kline_cached.get_next_kline()
    if kline is None:
        break

    strategy.run(kline)

print(strategy.first_kline.close_price)
print(strategy.last_kline.close_price)

base_balance, quote_balance = context.get_currency_balances()
print(base_balance * strategy.last_kline.close_price + quote_balance)

base_fee, quote_fee = context.get_exchange_fee()
print(base_fee * strategy.last_kline.close_price + quote_fee)

