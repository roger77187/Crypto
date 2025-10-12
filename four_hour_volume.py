import time
from datetime import datetime, timedelta
import pandas as pd
from utils import get_kline, calculate_recent_average
from itertools import cycle
from notify import dingtalk_notify

# 币种列表
symbols = ["ETHUSDT", "HYPEUSDT", "SUIUSDT", "XRPUSDT", "LTCUSDT", "DOGEUSDT", "LINKUSDT" , "ADAUSDT" , "WLFIUSDT", "SOLUSDT"]

webhook = "https://oapi.dingtalk.com/robot/send?access_token=7cec8580bca47a2ce6296bfc3db372f4d01e4a1db7a7caec472aa00fe16b61c7"

# 查询并处理各币种的成交量
def check_volume(symbol, proxy_cycle):
    # 读取4小时K线最新96根数据
    data = get_kline(symbol, "4h", 96, proxy_cycle)
    if not data or len(data) < 15:
        print(f"❌ {symbol} 数据不足以计算MA14")
        return
    # 提取成交量（第6个字段）
    volumes = [float(k[5]) for k in data]
    # 最近一个完整K线（倒数第二根）
    last_volume = volumes[-2]
    prev_volume = volumes[-3]  
    # 计算 MA14（不包含当前未完成的K线）
    ma14 = sum(volumes[-15:-1]) / 14
    # print(f"{symbol} 最近一根4H成交量: {last_volume}")
    # print(f"{symbol} 上一个4H成交量: {prev_volume}")
    # print(f"{symbol} 成交量MA14: {ma14:.2f}")
    if(last_volume < 0.5 * ma14 and last_volume < 0.5 * prev_volume):
        now = datetime.now()
        content=f"Lucky:🚨\n {now.strftime('%H:%M:%S')} \n {symbol}最近4小时K线显著缩量！！！" 
        dingtalk_notify(webhook, content)


# 定时执行任务：每小时的特定时刻检查成交量
def schedule_volume_check(proxy_cycle):

    while True:
        now = datetime.now()
        # 每隔4小时运行：
        if now.hour in [0, 4, 8, 12, 16, 20,] and now.minute == 3 and now.second == 1:
            print(f"⚡ {now.strftime('%H:%M:%S')} 开始检查前面4个小时的成交量...")
            for symbol in symbols:
                # 每个代币取完数休息，避免请求频繁被币安屏蔽
                time.sleep(1)
                check_volume(symbol, proxy_cycle)


# 启动定时任务
if __name__ == "__main__":
    proxy_ports = [42011, 42012, 42013, 42014, 42002, 42003, 42004, 42021, 42022]
    proxy_cycle = cycle(proxy_ports)  # 轮询器
    
    print(f"4小时K线缩量的定时程序已经启动...请勿关闭窗口！")
    schedule_volume_check(proxy_cycle)  
    # for symbol in symbols:
    #    check_volume(symbol, proxy_cycle)
