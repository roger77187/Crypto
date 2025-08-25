import requests
from utils import get_kline
from itertools import cycle

# 从日K线数据判断价格趋势，1表示上升趋势，-1表示下降趋势，0表示趋势未明
def trend(symbol, proxy_cycle)-> int:
    daily = get_kline(symbol, interval="1d", limit=30, proxy_cycle=proxy_cycle)
    if not daily or len(daily) < 30:
        print(f"❌ 无法获取 {symbol} 的K线数据")
        return 0
    # 提取日K线数据中的收盘价
    closes = [float(k[4]) for k in daily]
    # 当天的价格MA14
    window = closes[-14:]
    ma14 = sum(window) / 14
    # print(f"今天的MA14: {ma14}")
    # 前一天的价格MA14    
    window = closes[-15:-1]
    previous_ma14 = sum(window) / 14
    # print(f"昨天的MA14: {previous_ma14}")
    # 当天的价格MA7
    window = closes[-7:]
    ma7 = sum(window) / 7
    # print(f"今天的MA7: {ma7}")
    # 前一天的价格MA7
    window = closes[-8:-1]
    previous_ma7 = sum(window) / 7
    # print(f"昨天的MA7: {previous_ma7}")
    # 当天的收盘价
    current_close = closes[-1]
    # MA14和MA7同时上升，并且收盘价站在MA14之上
    if ma14 > previous_ma14 and ma7 > previous_ma7 and current_close > ma14:
        return 1
    # MA14和MA7同时下降，并且收盘价落在MA14之下    
    elif ma14 < previous_ma14 and ma7 < previous_ma7 and current_close < ma14:
        return -1
    else:
        return 0


# 示例调用
if __name__ == "__main__":
    # 模拟代理循环器
    proxy_ports = [42010, 42011, 42012]
    proxy_cycle = cycle(proxy_ports)
    symbols = ["BTCUSDT", "ETHUSDT", "AAVEUSDT", "TIAUSDT","LTCUSDT"]
    for sym in symbols:
        result = trend(sym,proxy_cycle)
        if result == 1:
            print(f"📈 {sym} 处于上升趋势")
        elif result == -1:
            print(f"📉 {sym} 处于下降趋势")
        else:
            print(f"➖{sym} 趋势不明")
