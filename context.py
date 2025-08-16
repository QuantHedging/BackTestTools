#!/usr/bin/env python
# encoding: utf-8
from enumeration import Side
from typing import Optional, List, Tuple

from _decimal import Decimal

from kline import KLine
from kline_cli import KLineSymbol, KLineInterval, get_next_klines
from order import Order


class BackTestContext(object):
    def __init__(self, kline_provider: str, symbol: KLineSymbol, interval: KLineInterval,
                 from_ts: int, end_ts: int = 4294967295):
        # K线数据源
        self.kline_provider: str = kline_provider
        # 交易对
        self.symbol: KLineSymbol = symbol
        # K线级别
        self.interval: KLineInterval = interval

        # 回测起止
        self.from_ts: int = from_ts
        self.end_ts: int = end_ts

        # 余额 [base资产]
        self.base_balance: Decimal = Decimal("0")
        # 余额 [quote资产]
        self.quote_balance: Decimal = Decimal("0")

        # 手续费消耗 [base资产]
        self.base_fee: Decimal = Decimal("0")
        # 手续费消耗 [quote资产]
        self.quote_fee: Decimal = Decimal("0")

        # 设定费率 [不区分maker还是taker]
        self.fee_rate: Decimal = Decimal("0")
        # 订单记录
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

    def get_exchange_fee(self) -> Tuple[Decimal, Decimal]:
        return self.base_fee, self.quote_fee

    # 下单 [买]
    # 手续费为 base资产
    # base balance增加
    # quote balance减少
    def buy(self, buy_ts: int, price: Decimal, quantity: Decimal):
        fee = quantity * self.fee_rate
        self.base_balance += quantity - fee
        self.quote_balance -= price * quantity
        self.base_fee += fee
        assert self.quote_balance >= Decimal("0")
        order = Order(buy_ts, Side.Buy, price, quantity, fee)
        self.orders.append(order)

    # 下单 [卖]
    # 手续费为 quote资产
    # base balance减少
    # quote balance增加
    def sell(self, sell_ts: int, price: Decimal, quantity: Decimal):
        self.base_balance -= quantity
        assert self.base_balance >= Decimal("0")
        fee = price * quantity * self.fee_rate
        self.quote_balance += price * quantity - fee
        self.quote_fee += fee
        order = Order(sell_ts, Side.Sell, price, quantity, fee)
        self.orders.append(order)


class BackTestKLineCached(object):
    def __init__(self, context: BackTestContext):
        # 游标K线
        self.cursor_kline: Optional[KLine] = None
        # 下一条批量从数据源获取到K线的开始时间
        self.next_klines_start_ts: int = context.from_ts
        # 数据源已没有剩余K线
        self.no_left_klines: bool = False
        # 本地K线缓冲区
        self.cached_klines: List[KLine] = list()
        self.context: BackTestContext = context

    @staticmethod
    def get_interval(unit: str, digital: int):
        if unit == "m":
            digital *= 60
        elif unit == "h":
            digital *= 3600
        elif unit == "d":
            digital *= 86400
        return digital

    def get_next_kline(self) -> Optional[KLine]:
        # 本地缓冲区K线数据不足20条 且远程数据源仍有K线数据
        if len(self.cached_klines) < 20 and not self.no_left_klines:
            klines = get_next_klines(self.context.kline_provider, self.context.symbol, self.context.interval,
                                     self.next_klines_start_ts,
                                     1000)
            if klines is None or len(klines) == 0:
                self.no_left_klines = True
            else:
                unit = self.context.interval.value[-1]
                assert unit in ("s", "m", "h", "d")
                digital = int(self.context.interval.value[:-1])
                interval = BackTestKLineCached.get_interval(unit, digital)

                # 推算 next_klines_start_ts
                # 扩充本地K线缓冲区
                self.next_klines_start_ts = klines[-1]["open_time"] // 1000 + interval
                self.cached_klines.extend(
                    [
                        KLine(k["open_time"], Decimal(k["open_price"]), Decimal(k["close_price"]),
                              Decimal(k["high_price"]), Decimal(k["low_price"]))
                        for k in klines
                    ])

        if len(self.cached_klines) == 0:
            return None

        self.cursor_kline = self.cached_klines.pop(0)
        if self.cursor_kline.open_time / 1000 > self.context.end_ts:
            return None

        return self.cursor_kline
