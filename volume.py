import time
import requests
import platform
from datetime import datetime, timedelta
import pandas as pd
from utils import get_kline, calculate_recent_average
from itertools import cycle
from trend import is_uptrend, is_downtrend
from notify import notify

# 币种列表
symbols = ["TIAUSDT", "SUIUSDT", "ARBUSDT", "SOLUSDT", "AAVEUSDT", "XRPUSDT", "LTCUSDT", "DOGEUSDT",  "ADAUSDT"]

# 各代币是否上升趋势的字典
up_trend_map = {
    "TIAUSDT": False,
    "SUIUSDT": False,
    "ARBUSDT": False,
    "SOLUSDT": False,
    "AAVEUSDT": False,
    "XRPUSDT": False,
    "LTCUSDT": False,
    "DOGEUSDT": False,
    "ADAUSDT": False
}

# 各代币是否上升趋势的字典
down_trend_map = {
    "TIAUSDT": False,
    "SUIUSDT": False,
    "ARBUSDT": False,
    "SOLUSDT": False,
    "AAVEUSDT": False,
    "XRPUSDT": False,
    "LTCUSDT": False,
    "DOGEUSDT": False,
    "ADAUSDT": False
}

# 更新各代币日线趋势的字典
def update_trend_dict(proxy_cycle):
    for symbol in symbols:
        # 查询日线K线数据，判断代币是否处于上升趋势或者下降趋势
        up_trend_map[symbol] = is_uptrend(symbol, proxy_cycle)
        time.sleep(0.5)
        down_trend_map[symbol] = is_downtrend(symbol, proxy_cycle)
        time.sleep(0.5)
    
# 判断日线是否处于上升趋势
def query_up_trend(symbol):
    return up_trend_map.get(symbol, False)  # 如果不存在，返回默认 False

# 判断日线是否处于下降趋势
def query_down_trend(symbol):
    return down_trend_map.get(symbol, False)  # 如果不存在，返回默认 False

# 查询并处理各币种的成交量
def check_volume(symbol, proxy_cycle):

    # 查询日线K线数据，判断代币是否处于上升趋势或者下降趋势
    uptrend = query_up_trend(symbol)
    downtrend = query_down_trend(symbol)

    # 读取15分钟K线最新96根数据
    data = get_kline(symbol, "15m", 96, proxy_cycle)

    if not data:
        print(f"获取 {symbol} 的15分钟K线失败或返回为空")
        return   

    # 开盘价、收盘价、成交量转换数据类型
    opens = [float(k[1]) for k in data]   # 第2列是 开盘价
    highs = [float(k[2]) for k in data]   # 第3列是 最高价
    lows = [float(k[3]) for k in data]    # 第4列是 最低价
    closes = [float(k[4]) for k in data]  # 第5列是 收盘价
    volumes = [float(k[5]) for k in data]  # 取成交量（K线的第6个字段）


    if not volumes:
        return

    # 计算成交量的MA96
    volume_ma96 = calculate_recent_average(volumes, 96)
    # print(f"{symbol}成交量的MA96: {volume_ma96} ")
    if volume_ma96 is None:
        print(f"⚠️ {symbol} 的15分钟K线数据不足96根，跳过计算")
        return

    # 以收盘价计算价格的MA14
    price_ma14 = calculate_recent_average(closes, 14)
    # print(f"{symbol}收盘价的MA14: {price_ma14} ")

    # 获取当前15分钟K线的成交量（即该15分钟K线的部分成交量）
    current_volume = volumes[-1]
    current_open = opens[-1]
    current_close = closes[-1]
    current_low = lows[-1]
    current_high = highs[-1]

    # 开盘价相对MA14的偏离率
    open_deviation = 0
    # 盘中价相对MA14的最大偏离率
    max_deviation = 0
    # 成交量放大倍数
    volume_times = current_volume / volume_ma96

    
    # 开盘价低于MA14，说明当前15分钟K线处于下跌状态
    if (current_open < price_ma14):
        open_deviation = (price_ma14 - current_open) / current_open
        max_deviation = (price_ma14 - current_low) / current_low
    else:
        open_deviation = (current_open - price_ma14) / price_ma14
        max_deviation = (current_high - price_ma14) / price_ma14

    # print(f"{symbol}开盘价与MA14的偏离: {open_deviation:.1%} ")
    # print(f"{symbol}盘中价与MA14的最大偏离: {max_deviation:.1%} ")

    # 开盘价与MA14已经有偏离，避免刚从整理平台选择方向的情况
    if(open_deviation > 0.01) :

        # 价格趋势未明的情况下，默认的放量倍数是4.5倍
        volume_multiple = 4.5
        # 成交量放大倍数和MA14价格偏离率的偏移基准   
        factor_multiple = 0.16
        factor = volume_times * max_deviation

        # 逆势的情况，逆势操作的高要求
        if((uptrend and current_close / price_ma14 >1.01) or (downtrend and current_close / price_ma14 < 0.99)):
            volume_multiple = 6
            factor_multiple = 0.23

        # 顺势的情况，顺势操作可以降低要求
        if((uptrend and current_close / price_ma14 < 0.99) or (downtrend and current_close / price_ma14 > 1.01) ) :
            volume_multiple = 2.3
            factor_multiple = 0.08


        # 放量价格异动
        if factor >  factor_multiple:

            # 上一个时段已经通知过，就无需重复通知
            if(current_volume < volumes[-2]):
                print(f"⚠️ {symbol} 本时段成交量比上一时段小，不再重复通知")
                return

            # 查询放量的5分钟K线，收盘价作为买点，开盘价作为第一止盈点
            time.sleep(0.5)
            data = get_kline(symbol, "5m", 3, proxy_cycle)
            if not data or len(data) < 3:
                print("❌ {symbol} 的5分钟K线数据不足3根")
                return        
            # 找出成交量最大的那根K线
            max_kline = max(data, key=lambda k: float(k[5]))  # k[5] 是成交量
            open_price = float(max_kline[1])  # 开盘价
            # 提取每根K线的收盘价（第5个字段，索引4）
            close_prices = [float(kline[4]) for kline in data]
            # 默认是多单的情况下，买入价是5分钟K线的收盘价的最低价
            buy_price = min(close_prices)

            order = "多单"
            if(current_close > price_ma14) :
                order = "空单"
                buy_price = max(close_prices)

            # 仓位大小，为量能倍数乘以价格偏离数，量能越大、偏离越大，开的仓位越大
            position = factor * 100 * 100
            number = position / current_close * 2

            content=f"{symbol}\n 当前15分钟{volume_times:.1f}倍放量!  价格最大偏离{max_deviation:.1%}！\n 建议开仓{order}数量为{number:.2f}!\n 建议下单价格为{buy_price}! "
            notify(content)



# 定时执行任务：每小时的特定时刻检查成交量
def schedule_volume_check(proxy_cycle):

    while True:
        now = datetime.now()

        # 每隔一小时更新一下K线日线趋势
        if now.minute == 8 and  now.second == 30:
            print(f"⚡ {now.strftime('%H:%M:%S')} 更新日线趋势判断...")
            update_trend_dict(proxy_cycle)

        # 判断当前时间是否是指定的检查时刻：
        if now.minute in [14, 29, 44, 59] and now.second == 30:
            print(f"⚡ {now.strftime('%H:%M:%S')} 开始检查成交量...")
            for symbol in symbols:
                # 每个代币取完数休息，避免请求频繁被币安屏蔽
                time.sleep(1)
                check_volume(symbol, proxy_cycle)
        time.sleep(0.3)  # 每秒检查一次时间


# 启动定时任务
if __name__ == "__main__":
    proxy_ports = [42010, 42011, 42013, 42014, 42002, 42004]
    proxy_cycle = cycle(proxy_ports)  # 轮询器

    # 初始化日线趋势判断
    update_trend_dict(proxy_cycle)
    
    print(f"异常放量的定时程序已经启动...请勿关闭窗口！")
    schedule_volume_check(proxy_cycle)  
    #for symbol in symbols:
    #    check_volume(symbol, proxy_cycle)
