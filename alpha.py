import time
import requests
import platform
import pandas as pd
from itertools import cycle
from utils import fetch_with_proxy
from notify import dingtalk_notify
from datetime import datetime, time, timedelta  # Import the class 'time'
import time as time_module                      # Import the module 'time' as 'time_module'
import threading


# 币种列表   https://www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list
alpha_map = {
    "ALPHA_476": "KO",    
    "ALPHA_472": "GAIB",     
    "ALPHA_471": "DGRAM",    
    "ALPHA_469": "PIEVERSE",    
    "ALPHA_465": "TIMI",    
    "ALPHA_451": "BEAT",     
    "ALPHA_452": "BAY",    
    "ALPHA_450": "NB",
    "ALPHA_449": "BOS",        
    "ALPHA_448": "PIGGY"
}

# 钉钉群通知机器人的API地址
webhook = "https://oapi.dingtalk.com/robot/send?access_token=75b8fc4ce4e1e72a378175408c026243f0a554f2033c6148c942346ef2cb1cb0"
# 只取最近2根K线
klines_limit = 2
# 初始化字典，key是代币名，value是上一次告警时间
last_alert_time = {}

# --- 配置参数 ---
# 每日开始运行的小时
START_HOUR = 8
# 每日停止运行的小时 (不包含 18:00 本身)
END_HOUR = 23

# 通过最近的交易记录,判断价格是否基本无变化。max_volatility是允许的最高波动率，百分比，通常是百分之0.01，也就是万分之一
def isFlat(alphaId,proxy_cycle,max_volatility):
    url = f"https://www.binance.com/bapi/defi/v1/public/alpha-trade/agg-trades"
    params = {
        "symbol": alphaId + "USDT",
        "limit": 120         
    }
    data = fetch_with_proxy(url, params, proxy_cycle=proxy_cycle)

    # 代币名称
    alphaName = alpha_map.get(alphaId)      
    if not data:
        print("❌ {alphaName} 取回的数据为空或为 None")
        return False  
    # 访问 'data' 字段中的列表
    records = data.get("data", [])
    if not records:
        print("⚠️ {alphaName} 取回的数据中交易记录为空！")
        return False    
    # 提取价格并转换为浮点数
    # 使用列表推导式高效完成提取和转换
    prices_array = [float(item['p']) for item in records if 'p' in item]
    min_price = min(prices_array)
    max_price = max(prices_array) 
    # 计算波动率: (最高价 - 最低价) / 最低价 * 100%
    if min_price > 0:
        volatility_percentage = ((max_price - min_price) / min_price) * 100
    else:
        volatility_percentage = 0.0
    # print(f"最低成交价: {min_price:.10f}")
    # print(f"最高成交价: {max_price:.10f}")           
    # print(f"价格波动率: {volatility_percentage:.5f}%")
    # 检查价格是否在指定范围内
    if volatility_percentage <= max_volatility:
        # print(f"✅ 结论: 价格波动率在 {max_volatility}% 范围之内。")
        return True
    else:
        # print(f"❌ 结论: 价格波动率超出了 {max_volatility}% 范围。")
        return False

# 新开异步线程监控被提醒刷单的代币是否波动加剧
def higher_volatility(alphaId,proxy_cycle):
    while True:
        if not (isFlat(alphaId,proxy_cycle,0.015)):
            now = datetime.now()
            # 代币名称
            name = alpha_map.get(alphaId)            
            content=f"❌Alpha：\n {now.strftime('%H:%M:%S')} \n **{name}**  波动加大!!!!!!"
            # 钉钉群通知
            dingtalk_notify(webhook, content)
            # print(content)
            # 设置为可以重新再发出可刷告警
            last_alert_time[alphaId] = None
            break  # 退出循环，线程自动结束
        # 轮询间隔时间1秒钟
        time_module.sleep(1)


# 以Restful从币安获取1分钟K线数据
def get_alpha_kline(alphaId,proxy_cycle):
    url = f"https://www.binance.com/bapi/defi/v1/public/alpha-trade/klines"
    params = {
        "symbol": alphaId + "USDT",
        "interval": "1m",  # 1分钟K线
        "limit": klines_limit         
    } 
    return fetch_with_proxy(url, params, proxy_cycle=proxy_cycle) 


# 判断1分钟K线是否平稳，需要连续多根K线振幅都在0.01%之内
def isCandlestickStable(data):
    if not data:
        return False
    # 取出 data 字典中的 "data" 键
    klines = data["data"]
    if not klines:
        return False
    # print("原始返回长度:", len(klines))
    completed = klines[:-1]     # 保险措施，去掉最后一根未完成
    # print(f"共获得 {len(completed)} 根完整K线")
    for k in completed:
        open_price = float(k[1])
        close_price = float(k[4])
        # print(f"开盘价={open_price}, 收盘价={close_price}")
        if((close_price > 1.0001 * open_price) or (close_price < 0.9999 * open_price)):
            return False
    # print("走势平稳的1分钟K线原始数据:", klines)
    return True


# 判断指定Alpha指定代币的K线是否平稳
def check_price(alphaId, proxy_cycle):
    # 代币名称
    name = alpha_map.get(alphaId)    
    # print("检查代币价格:", name)
    # 1分钟K线是否走势平稳
    # klines = get_alpha_kline(alphaId, proxy_cycle)
    # if(isCandlestickStable(klines)):
    # 检查成交记录是否价格基本无变化
    if(isFlat(alphaId, proxy_cycle, 0.01)):
        # 判断代币是否应该告警，如果10分钟内有报警就无需重复，并更新字典。       
        now = datetime.now()
        # 代币的上一次告警时间
        last_time = last_alert_time.get(alphaId)
        if last_time is None or (now - last_time) > timedelta(minutes=10):
            content=f"✅Alpha：\n {now.strftime('%H:%M:%S')} \n **{name}**  暂时平稳......"
            # 钉钉群通知
            dingtalk_notify(webhook, content)
            # print(content)
            # 更新告警时间
            last_alert_time[alphaId] = now
            # 创建并启动线程，用来监控提醒刷单的代币的波动，传参数用 args=(..., ...)
            t = threading.Thread(target=higher_volatility, args=(alphaId, proxy_cycle))
            t.start()


# 定时执行任务：每1分钟的特定时刻检查成交量
def schedule_price_check(proxy_cycle):
    while True:
        now = datetime.now()
        current_time = now.time()
        # 检查当前时间是否在运行窗口内: [8:00:00, 23:00:00)
        if time(START_HOUR, 0) <= current_time < time(END_HOUR, 0):
            for alphaId in alpha_map:
                check_price(alphaId, proxy_cycle)
        time_module.sleep(60) 

# 启动定时任务
if __name__ == "__main__":
    proxy_ports = [42011, 42012, 42013, 42014, 42002, 42003, 42004, 42021, 42002, 42003, 42004]
    proxy_cycle = cycle(proxy_ports)  # 轮询器
    print(f"Alpha代币价格平稳监测程序已经启动...请勿关闭窗口！")
    schedule_price_check(proxy_cycle)
    # klines = get_alpha_kline("ALPHA_382", proxy_cycle)
    # isCandlestickStable(klines)
