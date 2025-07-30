import requests
import winsound
import threading

# 通知到钉钉的群里面
def send_dingtalk_msg(content):

    webhook = "https://oapi.dingtalk.com/robot/send?access_token=7cec8580bca47a2ce6296bfc3db372f4d01e4a1db7a7caec472aa00fe16b61c7"    

    msg = {
        "msgtype": "text",
        "text": {
            "content": content
        }
    }

    headers = {'Content-Type': 'application/json'}
    requests.post(webhook, json=msg, headers=headers)   


# 蜂鸣器函数
def beep_for_5s():
    """持续5秒的蜂鸣声（Windows）"""
    try:
        duration = 10000   # 持续10秒（10000毫秒）
        frequency = 1000  # 1000Hz高频警报音
        winsound.Beep(frequency, duration)
    except Exception as e:
        print(f"蜂鸣失败: {e}")    

# 发出通知
def notify(content):
    content = "Lucky:🚨\n" + content
    # 电脑屏幕打印日志
    print(content)
    # 通知到手机钉钉
    send_dingtalk_msg(content)
    # 电脑声音告警
    threading.Thread(target=beep_for_5s).start() 

if __name__ == "__main__":
    notify("通知测试")    


