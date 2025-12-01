import time
from datetime import datetime
from utils import get_kline, calculate_recent_average
from itertools import cycle
from trend import trend
from notify import dingtalk_notify

# 币种列表
symbols = ["ETHUSDT", "LTCUSDT", "BTCUSDT", "SOLUSDT"]

webhook = "https://oapi.dingtalk.com/robot/send?access_token=8a618559bef6178849439433ef9fe1e9a77a60eec9b45716acf18a1b6d4f8c05"

# 各代币是否上升趋势的字典
up_trend_map = {}

# 各代币是否上升趋势的字典
down_trend_map = {}

# 更新各代币日线趋势的字典
def update_trend_dict(proxy_cycle):

    # 没有声明的话，默认是局部变量
    global up_trend_map
    global down_trend_map
    # 先初始化为False
    up_trend_map = {symbol: False for symbol in symbols}
    down_trend_map = {symbol: False for symbol in symbols}
    for symbol in symbols:
        result = trend(symbol, proxy_cycle)
        if result == 1:
            print(f"📈 {symbol} 上升趋势")
            up_trend_map[symbol] = True
        elif result == -1:
            print(f"📉 {symbol} 下降趋势")
            down_trend_map[symbol] = True
        else:
            print(f"➖ {symbol} 趋势不明")
        time.sleep(0.5)


# 判断日线是否处于上升趋势
def query_up_trend(symbol):
    return up_trend_map.get(symbol, False)  # 如果不存在，返回默认 False

# 判断日线是否处于下降趋势
def query_down_trend(symbol):
    return down_trend_map.get(symbol, False)  # 如果不存在，返回默认 False

# 查询并处理各币种的成交量
def check_volume(symbol, proxy_cycle):

    # 当前时间
    now = datetime.now()
    # 查询日线K线数据，判断代币是否处于上升趋势或者下降趋势
    uptrend = up_trend_map[symbol]
    downtrend = down_trend_map[symbol]

    # 读取15分钟K线最新96根数据
    data = get_kline(symbol, "15m", 96, proxy_cycle)

    if not data:
        print(f"获取 {symbol} 的15分钟K线失败或返回为空")
        return   

    # 开盘价、收盘价、成交量转换数据类型
    opens = [float(k[1]) for k in data]   # 第2列是 开盘价
    closes = [float(k[4]) for k in data]  # 第5列是 收盘价
    volumes = [float(k[5]) for k in data]  # 取成交量（K线的第6个字段）

    if not volumes:
        return

    # 计算成交量的MA96
    volume_ma96 = calculate_recent_average(volumes, 96)
    if volume_ma96 is None:
        print(f"⚠️ {symbol} 的15分钟K线数据不足96根，跳过计算")
        return

    # 以收盘价计算价格的MA7
    price_ma7 = calculate_recent_average(closes, 7)

    # 获取当前15分钟K线的成交量（即该15分钟K线的部分成交量）
    current_volume = volumes[-1]
    current_open = opens[-1]
    current_close = closes[-1]


    # 开盘价相对MA7的偏离率
    open_deviation = 0
    # 成交量放大倍数
    volume_times = current_volume / volume_ma96

    
    # 开盘价低于MA7，说明当前15分钟K线处于下跌状态
    if (current_open < price_ma7):
        open_deviation = (price_ma7 - current_open) / current_open
    else:
        open_deviation = (current_open - price_ma7) / price_ma7


    # 价格趋势未明的情况下，默认的放量倍数是6倍
    volume_multiple = 5
    # 15分钟K线开盘价偏离MA7的基准，价格趋势未明的情况下默认偏离1%
    price_deviation = 0.008
    # 仓位大小，量能越大，代表分歧越大，开的仓位越大
    position = volume_times * 400

    # 逆势的情况，逆势操作的高要求      上涨趋势，涨幅过快或者下跌趋势，下跌过快
    if((uptrend and current_open > price_ma7 and current_close > price_ma7) or (downtrend and current_open < price_ma7 and price_ma7 > current_close)):
        volume_multiple = 7
        position = volume_times * 200
        price_deviation = 0.015

    # 顺势的情况，顺势操作可以降低要求     上涨趋势的回调或者下跌趋势的反弹
    if((uptrend and current_open < price_ma7 and price_ma7 > current_close) or (downtrend and current_open >  price_ma7 and price_ma7 < current_close) ) :
        # 顺势的放量可以小一点
        volume_multiple = 2.2
        position = volume_times * 800
        price_deviation = 0.003

    print(f"❌ {symbol}，放量倍数基准{volume_multiple:.1f}，开盘价偏离基准{price_deviation:.3f}")


    # 开盘价与MA7已经有偏离，避免刚从整理平台选择方向的情况
    if(open_deviation > price_deviation) :
        # 放量价格异动
        if volume_times >  volume_multiple:
            # 上一个时段已经通知过，就无需重复通知
            if(current_volume < volumes[-2] * 0.9):
                print(f"⚠️ {symbol} 本时段成交量比上一时段小，不再重复通知")
                return

            order = "多单"
            if(current_open > price_ma7) :
                order = "空单"

            number = position / current_close
            content=f"Lucky:🚨    ** {symbol} **\n {now.strftime('%H:%M:%S')}当前15分钟\n {volume_times:.1f}倍放量!\n 建议{order}开仓数量为{number:.2f}!\n"
            dingtalk_notify(webhook, content)



# BTC 5分钟K线爆量的监控
def volume_spike_five_minute(proxy_cycle):
    # 当前时间
    now = datetime.now()    
    # 读取5分钟K线最新96根数据
    data = get_kline("BTCUSDT", "5m", 96, proxy_cycle)
    if not data:
        print(f"获取BTC的5分钟K线失败或返回为空")
        return
    volumes = [float(k[5]) for k in data]  # 取成交量（K线的第6个字段）
    if not volumes:
        return
    # 计算成交量的MA96
    volume_ma96 = calculate_recent_average(volumes, 96)
    if volume_ma96 is None:
        print(f"⚠️ BTC的15分钟K线数据不足96根，跳过计算")
        return
    # 获取当前5分钟K线的成交量（即该5分钟K线的部分成交量）
    current_volume = volumes[-1]           
    # 成交量放大倍数
    volume_times = current_volume / volume_ma96
    if(volume_times > 9.5):
       content=f"Lucky:🚨    ** BTC **\n {now.strftime('%H:%M:%S')}\n 当前5分钟成交量放大{volume_times:.1%}倍！\n"
       dingtalk_notify(webhook, content)


# 定时执行任务：每小时的特定时刻检查成交量
def schedule_volume_check(proxy_cycle):

    while True:
        now = datetime.now()

        # 每隔15分钟更新一下K线日线趋势
        if now.minute in [10, 25, 40, 55] and now.second == 55:
            print(f"⚡ {now.strftime('%Y-%m-%d %H:%M:%S')} 更新日线趋势判断...")
            update_trend_dict(proxy_cycle)

        # 每隔5分钟监测BTC是否有异常放量
        if now.minute in [4, 9, 19, 24, 34, 39, 49, 54] and now.second == 50:
            print(f"⚡ {now.strftime('%Y-%m-%d %H:%M:%S')} 监测BTC异常放量...") 

        # 判断当前时间是否是指定的检查时刻：
        if now.minute in [14, 29, 44, 59] and now.second == 40:
            print(f"⚡ {now.strftime('%Y-%m-%d %H:%M:%S')} 开始检查成交量...")
            for symbol in symbols:
                check_volume(symbol, proxy_cycle)
                # 每个代币取完数休息，避免请求频繁被币安屏蔽
                time.sleep(0.3)

        # 完成一系列任务休眠1秒
        time.sleep(1) 


# 启动定时任务
if __name__ == "__main__":
    proxy_ports = [42011, 42012, 42013, 42014, 42002, 42003, 42004, 42021, 42022]
    proxy_cycle = cycle(proxy_ports)  # 轮询器

    # 初始化日线趋势判断
    update_trend_dict(proxy_cycle)
    
    print(f"异常放量的定时程序已经启动...请勿关闭窗口！")
    schedule_volume_check(proxy_cycle)  
    # for symbol in symbols:
    #    check_volume(symbol, proxy_cycle)
