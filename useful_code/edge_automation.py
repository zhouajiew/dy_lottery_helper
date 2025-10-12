# 比较旧的反反爬手段
# 想增强反反爬能力可以自行前往patchright-python(by Kaliiiiiiiiii-Vinyzu)项目:)

# 自动化下的Edge浏览器推荐设置
import json
import os
import threading
import time

from selenium import webdriver
from selenium.webdriver.edge.service import Service

# 获取当前文件所在的目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 构建相对路径
relative_path = os.path.join(current_dir)

def keep_alive():
    while True:
        time.sleep(1)

# 获取日志
def get_driver_logs():
    logs = driver.get_log("performance")

    for log in logs:
        logjson = json.loads(log["message"])["message"]
        # 获取Network日志
        if logjson['method'] == 'Network.responseReceived':
            params = logjson['params']
            requestUrl = params['response']

if __name__ == "__main__":
    # 设置用户数据目录的路径
    user_data_dir = f'{relative_path}/user/data/dir'

    edge_options = webdriver.EdgeOptions()
    # 保持登录会话信息
    edge_options.add_argument(f'--user-data-dir={user_data_dir}')
    # 无头模式
    # edge_options.add_argument('--headless')

    edge_options.add_argument("--disable-blink-features=AutomationControlled")
    edge_options.add_experimental_option('useAutomationExtension', False)
    edge_options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])

    service = Service(executable_path=f'{relative_path}/msedgedriver.exe')
    # 开启performance，记录日志
    edge_options.set_capability("ms:loggingPrefs", {'performance': 'ALL'})

    driver = webdriver.Edge(options=edge_options)
    # 浏览器大小
    driver.set_window_size(700, 600)
    # 浏览器位置
    driver.set_window_position(50, 200)

    # 设置超时时间
    driver.set_page_load_timeout(20)

    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0"
    })
    
    # 浏览器执行stealth.min.js文件里的代码以应对多数情况的反爬
    with open(f"{relative_path}/stealth.min.js") as f:
        js = f.read()
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": js
    })

    # 打开抖音官网
    driver.get('https://live.douyin.com/categorynew/4_103')
    
    t = threading.Thread(target=keep_alive)
    t.start()
