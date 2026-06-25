import time
from datetime import datetime
from utils import get_kline, calculate_recent_average
from itertools import cycle
from trend import trend
from notify import dingtalk_notify

# 币种列表
symbols = ["BTCUSDT", "ETHUSDT", "XRPUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT", "ADAUSDT", "LTCUSDT", "SUIUSDT", "LINKUSDT", "WLFIUSDT", "ZECUSDT"]
# K线趋势的币种列表
trend_symbols = ["BTCUSDT"]

webhook = "https://oapi.dingtalk.com/robot/send?access_token=8a618559bef6178849439433ef9fe1e9a77a60eec9b45716acf18a1b6d4f8c05"

# 各代币是否上升趋势的字典
up_trend_map = {}

# 各代币是否上升趋势的字典
down_trend_map = {}

# 更新各代币K线趋势的字典
def update_trend_dict(proxy_cycle):

    # 没有声明的话，默认是局部变量
    global up_trend_map
    global down_trend_map
    # 先初始化为False
    up_trend_map = {symbol: False for symbol in trend_symbols}
    down_trend_map = {symbol: False for symbol in trend_symbols}
    for symbol in trend_symbols:
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


# 判断K线是否处于上升趋势
def query_up_trend(symbol):
    return up_trend_map.get(symbol, False)  # 如果不存在，返回默认 False

# 判断K线是否处于下降趋势
def query_down_trend(symbol):
    return down_trend_map.get(symbol, False)  # 如果不存在，返回默认 False

# 15分钟K线的异常放量
# 监控BTC、ETH
def volume_ma_15m(symbol, proxy_cycle):

    # 当前时间
    now = datetime.now()
    # 查询K线数据，判断代币是否处于上升趋势或者下降趋势
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

    # 以收盘价计算价格的MA14
    price_ma14 = calculate_recent_average(closes, 14)

    # 获取当前15分钟K线的成交量（即该15分钟K线的部分成交量）
    current_volume = volumes[-1]
    current_open = opens[-1]
    current_close = closes[-1]


    # 开盘价相对MA14的偏离率
    open_deviation = 0
    # 收盘价相对MA14的偏离率
    close_deviation = 0
    # 成交量放大倍数
    volume_times = current_volume / volume_ma96

    
    # 开盘价低于MA14，说明当前15分钟K线处于下跌状态
    if (current_open < price_ma14):
        open_deviation = (price_ma14 - current_open) / current_open
        close_deviation = (price_ma14 - current_close) / current_close
    else:
        open_deviation = (current_open - price_ma14) / price_ma14
        close_deviation = (current_close - price_ma14) / price_ma14


    # 超级异常放量情况，15分钟K线下跌5%，成交量放大10倍
    if (open_deviation * volume_times > 0.5):
            content=f"Lucky:🚨    ** {symbol} **\n {now.strftime('%H:%M:%S')}当前15分钟\n {volume_times:.1f}倍放量!\n 涨跌幅: {open_deviation:.1%}!\n"
            dingtalk_notify(webhook, content)
            return


    # 成交量放大倍数和收盘价偏移量

    # 价格趋势未明的情况下，默认的放量倍数是6倍
    volume_multiple = 6
    # 15分钟K线开盘价偏离MA14的基准，价格趋势未明的情况下默认偏离0.3%
    open_deviation_threshold = 0.003
    # 15分钟K线收盘价格偏离MA14和成交量放大倍数的乘积的基准，越大表示反抽动能越大
    price_volume_deviation_threshold = 0.025 * volume_multiple
    # 仓位大小，量能越大，代表分歧越大，开的仓位越大
    position = volume_times * 200


    # 顺势的情况，顺势操作可以降低要求     上涨趋势的回调或者下跌趋势的反弹
    if((uptrend and current_open < price_ma14 and price_ma14 > current_close) or (downtrend and current_open >  price_ma14 and price_ma14 < current_close) ) :
        # 顺势的放量可以小一点
        volume_multiple = 2.5
        open_deviation_threshold = 0.0
        price_volume_deviation_threshold = 0.01 * volume_multiple

    # print(f"❌ {symbol}，放量倍数基准{volume_multiple:.1f}，开盘价偏离基准{open_deviation_threshold:.3f}")


    # 开盘价与MA7已经有偏离，避免刚从整理平台选择方向的情况
    if(open_deviation > open_deviation_threshold) :
        # 放量价格异动
        if close_deviation * volume_times >  price_volume_deviation_threshold:
            # 上一个时段已经通知过，就无需重复通知
            if(current_volume < volumes[-2] * 0.8):
                print(f"⚠️ {symbol} 本时段成交量比上一时段小，不再重复通知")
                return

            order = "多单"
            if(current_open > price_ma14) :
                order = "空单"

            number = position / current_close
            content=f"Lucky:🚨    ** {symbol} **\n {now.strftime('%H:%M:%S')}当前15分钟\n {volume_times:.1f}倍放量!\n 建议{order}开仓数量为{number:.2f}!\n"
            dingtalk_notify(webhook, content)



# BTC 5分钟K线爆量的监控
def volume_ma_5m(proxy_cycle):
    volume_surge("BTCUSDT", "5m", 96, 7, proxy_cycle)

# 1小时K线爆量的监控
def volume_ma_1h(symbol, proxy_cycle):
    volume_surge(symbol, "1h", 96, 9.5, proxy_cycle)

# 4小时K线的显著缩量判断上涨趋势，取当前的上一个完整周期来分析
# 价格的MA14、30多头排列，当前价格与MA14偏离不超过0.5%
# 成交量不到MA14的一半，不到上上一周期的一半
def volume_ma_4h(symbol, proxy_cycle):
    # 读取4小时K线最新96根数据
    data = get_kline(symbol, "4h", 96, proxy_cycle)
    if not data or len(data) < 32:
        print(f"❌ {symbol} 数据不足以计算MA30")
        return
    # 显著缩量的情况，缩量意味着趋势的延续
    # 提取成交量（第6个字段）
    volumes = [float(k[5]) for k in data]  # 第6列是 成交量
    # 上一周期（倒数第2根，完整周期）的成交量
    last_volume = volumes[-2]
    # 上上周期的成交量
    prev_volume = volumes[-3]   
    # 计算 MA14（不包含当前未完成的K线）
    last_volume_ma14 = sum(volumes[-15:-1]) / 14
    last_volume_ma5 = sum(volumes[-6:-1]) / 5
    # print(f"{symbol} 上一周期4H成交量: {last_volume}")
    # print(f"{symbol} 上上周期4H成交量: {prev_volume}")
    # print(f"{symbol} 上一周期成交量MA14: {volume_ma14:.2f}")
    if(last_volume < 0.5 * last_volume_ma14 and last_volume < 0.6 * last_volume_ma5): 

        closes = [float(k[4]) for k in data]  # 第5列是 收盘价
        # 上一周期（倒数第二根，完整周期）的收盘价
        last_price = closes[-2]
        print(f"{symbol} 上一周期收盘价{last_price}")
        last_price_ma14 = sum(closes[-15:-1]) / 14
        prev_price_ma14 = sum(closes[-16:-2]) / 14
        # print(f"{symbol} 价格MA14: 上一周期{last_price_ma14},上上周期{prev_price_ma14}")
        last_price_ma30 = sum(closes[-31:-1]) / 30
        prev_price_ma30 = sum(closes[-32:-2]) / 30
        # print(f"{symbol} 价格MA30: 上一周期{last_price_ma30},上上周期{prev_price_ma30}")

        # 价格多头走势： MA30呈上升趋势，MA14高于MA30或者MA14呈上升趋势
        # 上一周期的收盘价与MA14或者MA30之间偏离度不超过0.005
        if( (last_price_ma14 > prev_price_ma14 or last_price_ma14 > last_price_ma30) and last_price_ma30 > prev_price_ma30  and  (abs(last_price - last_price_ma14) < 0.005 or abs(last_price - last_price_ma30) < 0.005)  ):
            # 当前时间
            now = datetime.now()
            content=f"Lucky:🚨  {now.strftime('%H:%M:%S')}  ** {symbol} **4小时K线缩量上涨\n"
            dingtalk_notify(webhook, content)




# 判断K线的是否放量异常
# symbol 代币的永续合约名称
# interval K线周期，如15分钟K线、1小时K线
# period  均线周期，如MA14、MA96
# threshold 触发放量新号的成交量倍数阈值
def volume_surge(symbol, interval, period, threshold, proxy_cycle):

    # 当前时间
    now = datetime.now() 
    # 读取1小时K线最新period + 1根数据，包括当前时间未完成的K线
    data = get_kline(symbol, interval, period + 1, proxy_cycle)
    if not data:
        print(f"获取{symbol}的{interval} K线失败或返回为空")
        return
     # 去掉最后一根未完成K线
    completed = data[:-1] 
    volumes = [float(k[5]) for k in completed]  # 取成交量（K线的第6个字段）
    # 计算成交量的period周期的平均值
    volume_ma = calculate_recent_average(volumes, period)
    if volume_ma is None:
        print(f"⚠️ {symbol}的{interval} K线数据不足{period}根，跳过计算")
        return
    # 获取最新一根完整K线的成交量
    current_volume = volumes[-1] 
    # 成交量放大倍数
    volume_times = current_volume / volume_ma
    print(f"⚡ {now.strftime('%Y-%m-%d %H:%M:%S')} ** {symbol} **最近{interval}成交量{current_volume:.1f}   成交量均值{volume_ma:.1f}！\n")
    if(volume_times > threshold):
       content=f"Lucky:🚨    ** {symbol} **\n {now.strftime('%H:%M:%S')}\n 最近{interval}成交量放大{volume_times:.1f}倍！\n"
       dingtalk_notify(webhook, content)




# 定时执行任务：每小时的特定时刻检查成交量
def schedule_volume_check(proxy_cycle):

    while True:

        now = datetime.now()

        # 每隔15分钟更新一下K线趋势
        if( now.minute in [10, 25, 40, 55] and now.second == 55 ):
            # print(f"⚡ {now.strftime('%Y-%m-%d %H:%M:%S')} 更新K线趋势判断...")
            update_trend_dict(proxy_cycle)

        # 1小时K线监控，新的1小时15秒开始
        if( now.minute == 0 and now.second == 15 ):
            print(f"⚡ {now.strftime('%Y-%m-%d %H:%M:%S')} 开始检查1小时成交量...")
            for symbol in symbols:
                volume_ma_1h(symbol, proxy_cycle)
                # 每个代币取完数休息，避免请求频繁被币安屏蔽
                time.sleep(0.5) 

        # 15分钟K线监控，每个刻钟结束前的10秒钟开始
        # 只监控BTC和ETH
        if( now.minute in [14, 29, 44, 59] and now.second == 30):
            print(f"⚡ {now.strftime('%Y-%m-%d %H:%M:%S')} 开始检查15分钟成交量...")
            volume_ma_15m( "BTCUSDT", proxy_cycle)
            # 每个代币取完数休息，避免请求频繁被币安屏蔽
            time.sleep(0.5) 
            # volume_ma_15m( "ETHUSDT", proxy_cycle)

        # 4小时K线监控，第3分钟开始
        if( now.hour % 4 == 0 and now.minute == 3 and now.second == 1):
            print(f"⚡ {now.strftime('%Y-%m-%d %H:%M:%S')} 开始检查4小时K线...")
            for symbol in symbols:
                volume_ma_4h(symbol, proxy_cycle)
                # 每个代币取完数休息，避免请求频繁被币安屏蔽
                time.sleep(3)


        # 5分钟K线监控，新的5分钟的第3秒开始
        # if now.minute in [0, 5, 20, 25, 35, 40, 50, 55] and now.second == 2:
        #    # print(f"⚡ {now.strftime('%Y-%m-%d %H:%M:%S')} 监测BTC异常放量...") 
        #    volume_ma_5m(proxy_cycle)


        # 完成一系列任务休眠1秒
        time.sleep(1) 


# 启动定时任务
if __name__ == "__main__":
    proxy_ports = [42011, 42012, 42013, 42014, 42002, 42003, 42004, 42021, 42022]
    proxy_cycle = cycle(proxy_ports)  # 轮询器

    # 初始化日线趋势判断
    update_trend_dict(proxy_cycle)

    # 测试5分钟K线监控
    # volume_ma_5m(proxy_cycle)

    # 测试15分钟K线监控
    # for symbol in symbols:
    #    volume_ma_15m(symbol, proxy_cycle)

    # 测试4小时K线监控
    # for symbol in symbols:
    #    volume_ma_4h(symbol, proxy_cycle)
    
    print(f"异常放量的定时程序已经启动...请勿关闭窗口！")

    schedule_volume_check(proxy_cycle)

