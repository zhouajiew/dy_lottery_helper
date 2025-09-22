# 为selenium添加需要账号与密码的代理
# Edge浏览器的用法
import string
import time
import threading

import zipfile

from selenium.webdriver import Edge
from selenium.webdriver import EdgeOptions

def create_proxyauth_extension(proxy_host, proxy_port,
                               proxy_username, proxy_password,
                               scheme='http', plugin_path=None):
    """代理认证插件

    args:
        proxy_host (str): 你的代理地址或者域名（str类型）
        proxy_port (int): 代理端口号（int类型）
        proxy_username (str):用户名（字符串）
        proxy_password (str): 密码 （字符串）
    kwargs:
        scheme (str): 代理方式 默认http
        plugin_path (str): 扩展的绝对路径

    return str -> plugin_path
    """

    if plugin_path is None:
        plugin_path = 'chrome_proxyauth_plugin.zip'

    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version":"22.0.0"
    }
    """

    background_js = string.Template(
        """
        var config = {
                mode: "fixed_servers",
                rules: {
                  singleProxy: {
                    scheme: "${scheme}",
                    host: "${host}",
                    port: parseInt(${port})
                  },
                  bypassList: ["foobar.com"]
                }
              };

        chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

        function callbackFn(details) {
            return {
                authCredentials: {
                    username: "${username}",
                    password: "${password}"
                }
            };
        }

        chrome.webRequest.onAuthRequired.addListener(
                    callbackFn,
                    {urls: ["<all_urls>"]},
                    ['blocking']
        );
        """
    ).substitute(
        host=proxy_host,
        port=proxy_port,
        username=proxy_username,
        password=proxy_password,
        scheme=scheme,
    )
    with zipfile.ZipFile(plugin_path, 'w') as zp:
        zp.writestr("manifest.json", manifest_json)
        zp.writestr("background.js", background_js)

    return plugin_path

def keep_alive():
    while True:
        time.sleep(1)

if __name__ == "__main__":
    # 用户名
    username = "aaa"
    # 密码
    password = "bbb"
    # IP
    proxy_ip = "xx.xx.xx.xx"
    # IP端口号
    proxy_port = "yyyy"

    proxyauth_plugin_path = create_proxyauth_extension(
        proxy_host=proxy_ip,
        proxy_port=proxy_port,
        proxy_username=username,
        proxy_password=password
    )

    edge_options = EdgeOptions()

    edge_options.add_extension(proxyauth_plugin_path)
    edge_options.add_argument(f'--proxy-server=http://{proxy_ip}:{proxy_port}')

    driver = Edge(options=edge_options)
    driver.get("http://httpbin.org/ip")

    t = threading.Thread(target=keep_alive)
    t.start()
