#!/usr/bin/env python
# encoding: utf-8
from typing import List, Optional

from _decimal import Decimal, ROUND_DOWN

from context import BackTestContext, KLine, Order
from strategies import IStrategy


class MovingAverageTrendStrategy(IStrategy):
    def __init__(self, context: BackTestContext,
                 kline_wnd_size: int, avg_line_wnd_size: int,
                 buy_volatility_rate: Decimal, sell_volatility_rate: Decimal, drawdown_rate: Decimal):
        IStrategy.__init__(self, context)
        # K线滑动窗口大小
        self.kline_wnd_size: int = kline_wnd_size
        # 均线线滑动窗口大小
        self.avg_line_wnd_size: int = avg_line_wnd_size
        # 波动率阈值 [触发买入]
        self.buy_volatility_rate: Decimal = buy_volatility_rate
        # 波动率阈值 [触发卖出]
        self.sell_volatility_rate: Decimal = sell_volatility_rate
        # 亏损率 [触发止损]
        self.drawdown_rate: Decimal = drawdown_rate
        # K线滑动窗口
        self.kline_wnd: List[KLine] = list()
        # 均线线滑动窗口
        self.avg_line_wnd: List[Decimal] = list()
        self.first_kline: Optional[KLine] = None
        self.last_kline: Optional[KLine] = None
        self.last_buy_order: Optional[Order] = None

    def run(self, kline: KLine):
        if self.first_kline is None:
            self.first_kline = kline
        self.last_kline = kline

        self.kline_wnd.append(kline)
        if len(self.kline_wnd) > self.kline_wnd_size:
            self.kline_wnd.pop(0)

        if len(self.kline_wnd) < self.kline_wnd_size:
            return

        # 收盘价计算均线价格
        avg_price: Decimal = sum(list(map(lambda x: x.close_price, self.kline_wnd))) / Decimal(self.kline_wnd_size)
        self.avg_line_wnd.append(avg_price)
        if len(self.avg_line_wnd) > self.avg_line_wnd_size:
            self.avg_line_wnd.pop(0)

        if len(self.avg_line_wnd) < self.avg_line_wnd_size:
            return

        # 需满足K线滑动窗口和均线滑动窗口都满载的情况下才会进行开始运行策略
        # 以下为简单的示例策略 只有空仓和满仓两个状态
        base_balance, quote_balance = self.context.get_currency_balances()
        if base_balance > Decimal("0"):
            # 满仓状态
            avg_max = max(self.avg_line_wnd)
            volatility = (avg_max - self.avg_line_wnd[-1]) / avg_max

            if volatility >= self.sell_volatility_rate:
                # 形态为向下趋势 并且超过阈值 [卖]
                sell_price = kline.close_price
                print("Sell:", sell_price, base_balance)
                self.context.sell(kline.open_time, sell_price, base_balance)

            if (kline.close_price - self.last_buy_order.price) / self.last_buy_order.price < -self.drawdown_rate:
                # 浮亏已超过设定的止损率 [卖]
                sell_price = kline.close_price
                print("Sell:", sell_price, base_balance)
                self.context.sell(kline.open_time, sell_price, base_balance)
        else:
            # 空仓状态
            avg_min = min(self.avg_line_wnd)
            volatility = (self.avg_line_wnd[-1] - avg_min) / avg_min

            if volatility >= self.buy_volatility_rate:
                # 形态为向上趋势 并且超过阈值 [买]
                buy_price = kline.close_price
                quantity = quote_balance / buy_price
                quantity = quantity.quantize(Decimal("0.0000"), rounding=ROUND_DOWN)
                print("Buy:", buy_price, quantity)
                self.context.buy(kline.open_time, buy_price, quantity)
                self.last_buy_order = self.context.orders[-1]
