import time
import requests
from itertools import cycle


headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Connection": "close"
}

# 轮询代理服务器
def get_next_proxy(proxy_cycle):
    port = next(proxy_cycle)
    return {
        "http": f"http://127.0.0.1:{port}",
        "https": f"http://127.0.0.1:{port}"
    }


# 选择不同的代理服务器去访问目标网站
def fetch_with_proxy(url, params=None, retries=3, timeout=10, proxy_cycle=None):

    if proxy_cycle is None:
        raise ValueError("proxy_cycle 参数不能为空")

    for attempt in range(retries):
        proxies = get_next_proxy(proxy_cycle)
        try:
            r = requests.get(url, params=params, proxies=proxies, headers=headers, timeout=timeout)
            r.raise_for_status()
            # print(r.url)
            # print(r.status_code)
            # print(r.text)
            return r.json()
        except requests.exceptions.SSLError as ssl_err:
            print(f"❌ SSL错误（代理 {proxies['http']}）: {ssl_err}")
        except requests.exceptions.ProxyError as p_err:
            print(f"❌ 代理连接失败（{proxies['http']}）: {p_err}")
        except Exception as e:
            print(f"⚠️ 请求失败（代理 {proxies['http']}）: {e}")
        time.sleep(1)  # 可适当加长
    return None


# 简单测试
if __name__ == "__main__":
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    proxy_ports = [42010, 42011, 42012]
    proxy_cycle = cycle(proxy_ports)  # 轮询器
    url = "https://fapi.binance.com/fapi/v1/ticker/price"
    for symbol in symbols:
        price = fetch_with_proxy(url, params={"symbol": symbol}, proxy_cycle=proxy_cycle)
        if price:
            print(f"{symbol} 合约最新价格：{price['price']}")
        time.sleep(1)
