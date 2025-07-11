import time
import requests
import threading
import platform
from datetime import datetime, timedelta
import pandas as pd

# 币种列表
symbols = ["TIAUSDT", "SUIUSDT", "ARBUSDT", "SOLUSDT", "AAVEUSDT", "XRPUSDT", "LTCUSDT", "DOGEUSDT", "ETHUSDT"]

# Binance API 地址
BASE_URL = "https://fapi.binance.com/"

pushkey = "PDU35961TPdv1z3nSCKLpXehgf1lEZ0AoROwsKKcX"

# 设置代理（如有）
proxies = {
    "http": "http://127.0.0.1:42010",     # 视你的代理工具而定
    "https": "http://127.0.0.1:42010"
}


# 推送告警到手机上的PushDeer
def pushdeer_notify(title, message, pushkey="PDU35961TPdv1z3nSCKLpXehgf1lEZ0AoROwsKKcX"):
    url = f"https://api2.pushdeer.com/message/push"
    params = {
        "pushkey": pushkey,
        "text": title,
        "desp": message,
        "type": "markdown"  # 你也可以使用 'text'
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            print("✅ 已推送到手机")
        else:
            print(f"⚠️ 推送失败: {response.text}")
    except Exception as e:
        print(f"❌ 推送异常: {e}")

def notify(symbol, current_volume, ma96, multiplier, pushkey):
    message = (
        f"🚨 **{symbol} 成交量异常**\n\n"
        f"- 当前成交量: `{current_volume}`\n"
        f"- MA96: `{ma96}`\n"
        f"- 阈值: `{ma96 * multiplier}`\n"
    )
    pushdeer_notify("成交量预警", message, pushkey)  

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

# 以Restful从币安获取15分钟K线数据
def get_kline(symbol,limit=96):
    try:
        url = f"{BASE_URL}/fapi/v1/klines"
        params = {"symbol": symbol, "interval": "15m", "limit": limit}
        r = requests.get(url, params=params, proxies=proxies, timeout=10)
        return r.json()
    except Exception as e:
        print(f"❌ 获取K线失败: {symbol} {e}")
        return None


# 计算成交量的 MA96
def calculate_ma96(volumes):

    if len(volumes) < 96:
        return None
    return sum(volumes) / 96

# 计算成交价的 MA14
def caculate_ma14(prices):
    # 只取最后14个收盘价
    last_14_closes = prices[-14:]

    # 计算 MA14
    ma14 = sum(last_14_closes) / len(last_14_closes)
    return ma14


# 查询并处理各币种的成交量
def check_volume(symbol, multiplier=5):

    data = get_kline(symbol)

    if not data:
        print(f"获取 {symbol} 的K线失败或返回为空")
        return   

    # 开盘价、收盘价、成交量转换数据类型
    closes = [float(k[4]) for k in data]  # 第5列是 close
    opens = [float(k[1]) for k in data]  # 第2列是 close
    volumes = [float(k[5]) for k in data]  # 取成交量（K线的第6个字段）

    if not volumes:
        return

    # 计算 MA96
    volume_ma96 = calculate_ma96(volumes)
    # print(f"{symbol}成交量的MA96: {volume_ma96} ")
    if volume_ma96 is None:
        print(f"⚠️ {symbol} 的K线数据不足96根，跳过计算")
        return

    price_ma14 = caculate_ma14(closes)
    # print(f"{symbol}收盘价的MA14: {price_ma14} ")

    # 获取当前15分钟K线的成交量（即该15分钟K线的部分成交量）
    current_volume = volumes[-1]
    current_open = opens[-1]
    current_close = closes[-1]

    open_deviation = abs(current_open - price_ma14) / price_ma14
    # print(f"{symbol}开盘价与MA14的偏离: {open_deviation} ")
    close_deviation = abs(current_close - price_ma14) / price_ma14
    # print(f"{symbol}收盘价与MA14的偏离: {close_deviation} ")


    # 比较成交量是否超过 MA96 的指定倍数
    if current_volume > volume_ma96 * multiplier and open_deviation > 0.005 and close_deviation > 0.02:
        # print(f"🚨 {symbol} 当前15分钟成交量 ({current_volume}) 超过 MA96 ({volume_ma96 * multiplier}) 的{multiplier}倍！")
        # 仓位大小，为量能倍数乘以偏离数，量能越大、偏离越大，开的仓位越大
        position = current_volume / volume_ma96 *  close_deviation * 100 * 100
        number = position / current_close
        print(f"🚨 {symbol} 当前15分钟{multiplier}倍放量！价格偏离{close_deviation}！建议合约下单数量为{number:.2f}")
        # 通知到手机端
        # notify(symbol, current_volume, volume_ma96, multiplier, pushkey)
        threading.Thread(target=beep_for_5s).start()

# 定时执行任务：每小时的特定时刻检查成交量
def schedule_volume_check(multiplier=5):

    while True:
        now = datetime.now()

        # 判断当前时间是否是指定的检查时刻：
        if now.minute in [14, 29, 44, 59] and now.second == 30:
            print(f"⚡ {now.strftime('%H:%M:%S')} 开始检查成交量...")
            for symbol in symbols:
                # 每个代币取完数休息，避免请求频繁被币安屏蔽
                time.sleep(0.3)
                check_volume(symbol, multiplier)
        time.sleep(0.5)  # 每秒检查一次时间


# 启动定时任务
if __name__ == "__main__":
    # 在这里传入你需要的倍数值，例如 4倍，10倍等
    schedule_volume_check(multiplier=4)  # 默认是5倍，可以根据需求传递不同倍数
    #for symbol in symbols:
    #    check_volume(symbol, multiplier=4)
