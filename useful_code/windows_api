import ctypes

if __name__ == "__main__":
    # 关键！！设置LockSetForegroundWindow的值为1使其它程序无法调用SetForegroundWindow方法
    # 这样做是为了防止Selenium频繁将浏览器窗口放在最前面以及占用窗口焦点
    # 禁用了SetForegroundWindow方法也不会对Selenium产生影响，因为这和在PyCharm里运行的效果是一样的
    ctypes.windll.user32.LockSetForegroundWindow(1)
