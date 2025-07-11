import time
import requests
import threading
import platform
from datetime import datetime, timedelta

# 币种列表
symbols = ["TIAUSDT", "SUIUSDT", "ARBUSDT", "SOLUSDT", "AAVEUSDT", "XRPUSDT", "LTCUSDT", "DOGEUSDT"]

# Binance API 地址
BASE_URL = "https://api.binance.com"

# 历史K线缓存
kline_cache = {}
last_kline_update = {}

# 设置代理（如有）
proxies = {
    "http": "http://127.0.0.1:42010",
    "https": "http://127.0.0.1:42010"
}

# 蜂鸣器函数
def beep_for_5s():
    system = platform.system()
    if system == "Windows":
        import winsound
        for _ in range(5):
            winsound.Beep(1000, 500)
    else:
        import os
        os.system('play -nq -t alsa synth 0.5 sine 880 repeat 10 || echo "\a"')

# 合并获取所有币种实时价格
def get_all_prices():
    try:
        url = f"{BASE_URL}/api/v3/ticker/price"
        r = requests.get(url, proxies=proxies, timeout=10)
        data = r.json()
        prices = {item['symbol']: float(item['price']) for item in data if item['symbol'] in symbols}
        return prices
    except Exception as e:
        print(f"❌ 获取合并价格失败: {e}")
        return {}

# 获取最近9根K线的close
def get_kline(symbol):
    try:
        url = f"{BASE_URL}/api/v3/klines"
        params = {"symbol": symbol, "interval": "15m", "limit": 9}
        r = requests.get(url, params=params, proxies=proxies, timeout=10)
        data = r.json()
        closes = [float(k[4]) for k in data]
        return closes
    except Exception as e:
        print(f"❌ 获取K线失败: {symbol} {e}")
        return []

# 主轮询逻辑
def poll_loop():
    while True:
        now = datetime.now()
        prices = get_all_prices()

        for symbol in symbols:
            # 每15分钟刷新K线
            if symbol not in last_kline_update or now - last_kline_update[symbol] >= timedelta(minutes=15):
                kline = get_kline(symbol)
                if kline:
                    kline_cache[symbol] = kline
                    last_kline_update[symbol] = now
                else:
                    continue

            # 实时价格
            price = prices.get(symbol)
            if price is None or symbol not in kline_cache or len(kline_cache[symbol]) < 9:
                continue

            # MA10 = 最近9根K线 + 实时价格
            closes = kline_cache[symbol]
            ma10 = (sum(closes) + price) / 10
            deviation = abs(price - ma10) / ma10

            print(f"{symbol}: 当前={price:.4f}, MA10={ma10:.4f}, 偏离={deviation:.2%}")

            if deviation > 0.03:
                print(f"🚨 {symbol} 偏离 MA10 超过 3%")
                threading.Thread(target=beep_for_5s).start()

        time.sleep(5)

# 启动
if __name__ == "__main__":
    poll_loop()
