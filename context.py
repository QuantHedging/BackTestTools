#!/usr/bin/env python
# encoding: utf-8
from enumeration import Side
from typing import Optional, List, Tuple

from _decimal import Decimal

from kline_cli import KLineSymbol, KLineInterval, get_next_klines


class KLine(object):
    def __init__(self, open_time: int, open_price: Decimal, close_price: Decimal, high_price: Decimal,
                 low_price: Decimal):
        self.open_time: int = open_time
        self.open_price: Decimal = open_price
        self.close_price: Decimal = close_price
        self.high_price: Decimal = high_price
        self.low_price: Decimal = low_price


class Order(object):
    def __init__(self, order_ts: int, side: Side, price: Decimal, quantity: Decimal, fee: Decimal):
        self.order_ts = order_ts
        self.side = side
        self.price = price
        self.quantity = quantity
        self.fee = fee


class BackTestContext(object):
    def __init__(self, kline_provider: str, symbol: KLineSymbol, interval: KLineInterval,
                 from_ts: int, end_ts: int = 4294967295):
        self.kline_provider: str = kline_provider
        self.symbol: KLineSymbol = symbol
        self.interval: KLineInterval = interval
        self.from_ts: int = from_ts
        self.end_ts: int = end_ts

        self.base_balance: Decimal = Decimal("0")
        self.quote_balance: Decimal = Decimal("0")
        self.fee_rate: Decimal = Decimal("0")

        self.orders: List[Order] = list()

    def init_currency_balances(self, base_balance: Decimal, quote_balance: Decimal):
        self.base_balance = base_balance
        self.quote_balance = quote_balance

    def init_exchange_fee_rate(self, fee_rate: Decimal):
        self.fee_rate = fee_rate

    def get_currency_balances(self) -> Tuple[Decimal, Decimal]:
        return self.base_balance, self.quote_balance

    def get_exchange_fee_rate(self) -> Decimal:
        return self.fee_rate

    def buy(self, buy_ts: int, price: Decimal, quantity: Decimal):
        fee = quantity * self.fee_rate
        self.base_balance += quantity - fee
        self.quote_balance -= price * quantity
        assert self.quote_balance >= Decimal("0")
        order = Order(buy_ts, Side.Buy, price, quantity, fee)
        self.orders.append(order)

    def sell(self, sell_ts: int, price: Decimal, quantity: Decimal):
        self.base_balance -= quantity
        assert self.base_balance >= Decimal("0")
        fee = price * quantity * self.fee_rate
        self.quote_balance += price * quantity - fee
        order = Order(sell_ts, Side.Sell, price, quantity, fee)
        self.orders.append(order)


class BackTestKLineCached(object):
    def __init__(self, context: BackTestContext):
        self.last_kline: Optional[KLine] = None
        self.cached_klines: List[KLine] = list()
        self.no_left_kline: bool = False
        self.context: BackTestContext = context

    def get_next_kline(self, from_ts: int) -> Optional[KLine]:
        if len(self.cached_klines) < 20 and not self.no_left_kline:
            klines = get_next_klines(self.context.kline_provider, self.context.symbol, self.context.interval, from_ts,
                                     1000)
            if len(klines) == 0:
                self.no_left_kline = True
            else:
                self.cached_klines.extend(
                    [
                        KLine(k["open_time"], Decimal(k["open_price"]), Decimal(k["close_price"]),
                              Decimal(k["high_price"]), Decimal(k["low_price"]))
                        for k in klines
                    ])

        if len(self.cached_klines) == 0:
            return None

        self.last_kline = self.cached_klines.pop(0)
        if self.last_kline.open_time / 1000 > self.context.end_ts:
            return None

        return self.last_kline
