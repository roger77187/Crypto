import requests
from utils import fetch_with_proxy
from itertools import cycle

# 使用代理轮询从币安合约API读取K线日线数据
def get_futures_kline(symbol, interval="1d", limit=30, proxy_cycle=None):
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    return fetch_with_proxy(url, params=params, proxy_cycle=proxy_cycle)


def get_recent_ma14_list(symbol, proxy_cycle):
    """
    获取 symbol 最近三天的 MA14 值 和 倒数第2天的收盘价。
    """
    data = get_futures_kline(symbol, interval="1d", limit=30, proxy_cycle=proxy_cycle)
    # print(f"✅ {symbol} 返回 {len(data) if data else 0} 条K线数据")
    if not data or len(data) < 30:
        print(f"❌ 无法获取 {symbol} 的K线数据")
        return None, None

    closes = [float(k[4]) for k in data]
    ma14_list = []

    for i in range(-3, 0):
        end_index = len(closes) + i + 1
        start_index = end_index - 14
        if start_index < 0:
            print(f"❌ {symbol} 数据不足以计算MA14（索引{i}）")
            return None, None
        window = closes[start_index:end_index]
        ma14 = sum(window) / 14
        ma14_list.append(ma14)

    prev_close = closes[-2]  # 倒数第2天的收盘价
    # print(f"{symbol} 收盘价数量: {len(closes)}")
    # print(f"最近3日收盘价: {closes[-3:]}")
    # print(f"最近14日收盘价: {closes[-14:]}")
    return ma14_list, prev_close



# 从日线数据判断是否处于上升趋势
def is_uptrend(symbol, proxy_cycle):
    """
    判断是否为上升趋势：
    MA14递增，且倒数第2天的收盘价 > 对应的MA14
    """
    ma14_list, prev_close = get_recent_ma14_list(symbol, proxy_cycle)
    if not ma14_list:
        return False

    if ma14_list[0] < ma14_list[1] < ma14_list[2] and prev_close > ma14_list[1]:
        # print(f"📈 {symbol} 处于上升趋势")
        return True
    else:
        # print(f"📉 {symbol} 不符合上升趋势条件")
        return False


def is_downtrend(symbol, proxy_cycle):
    """
    判断是否为下降趋势：
    MA14递减，且倒数第2天的收盘价 < 对应的MA14
    """
    ma14_list, prev_close = get_recent_ma14_list(symbol, proxy_cycle)
    if not ma14_list:
        return False

    if ma14_list[0] > ma14_list[1] > ma14_list[2] and prev_close < ma14_list[1]:
        # print(f"🔻 {symbol} 处于下降趋势")
        return True
    else:
        # print(f"📈 {symbol} 不符合下降趋势条件")
        return False

# 示例调用
if __name__ == "__main__":
    # 模拟代理循环器
    proxy_ports = [42010, 42011, 42012]
    proxy_cycle = cycle(proxy_ports)
    symbols = ["BTCUSDT", "ETHUSDT"]
    for sym in symbols:
        is_uptrend(sym, proxy_cycle)
        is_downtrend(sym, proxy_cycle)
