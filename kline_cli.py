#!/usr/bin/env python
# encoding: utf-8
import json
import requests

from enumeration import KLineSymbol, KLineInterval


def get_previous_klines(kline_provider: str, symbol: KLineSymbol, interval: KLineInterval, end_time: int,
                        limit: int, proxies: dict = None) -> list:
    assert limit <= 1000
    url = '{}/api/kline/{}/{}/previous?endTime={}&&limit={}' \
        .format(kline_provider, symbol.value, interval.value, end_time * 1000, limit)
    session = requests.Session()
    session.trust_env = False
    resp = session.get(url=url, proxies=proxies)
    return json.loads(resp.text)


def get_next_klines(kline_provider: str, symbol: KLineSymbol, interval: KLineInterval, from_time: int,
                    limit: int, proxies: dict = None) -> list:
    assert limit <= 1000
    url = '{}/api/kline/{}/{}/next?fromTime={}&&limit={}' \
        .format(kline_provider, symbol.value, interval.value, from_time * 1000, limit)
    session = requests.Session()
    session.trust_env = False
    resp = session.get(url=url, proxies=proxies)
    return json.loads(resp.text)
