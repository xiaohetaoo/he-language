# -*- coding: utf-8 -*-
"""量一下打包 exe 的启动耗时，并等窗口真正出现。

原来的 验exe界面.py 固定等 6 秒就去找窗口，启动稍慢就会误判成
「启动异常」。改成轮询等待，并打印到底花了多久。

用法：python 测试/量启动.py
"""

import ctypes
import os
import subprocess
import sys
import time
from ctypes import wintypes

这里 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
exe = os.path.join(这里, "dist", "核工坊Qt.exe")


def 找窗口():
    用户 = ctypes.windll.user32
    标题们 = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def 回调(hwnd, _):
        if 用户.IsWindowVisible(hwnd):
            长 = 用户.GetWindowTextLengthW(hwnd)
            if 长:
                缓 = ctypes.create_unicode_buffer(长 + 1)
                用户.GetWindowTextW(hwnd, 缓, 长 + 1)
                标题们.append(缓.value)
        return True

    用户.EnumWindows(回调, 0)
    return [t for t in 标题们 if "核工坊" in t]


起始 = time.time()
程序 = subprocess.Popen(
    [exe], cwd=这里, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
)
print("已启动 pid=%d，轮询等窗口…" % 程序.pid)

窗口 = []
截止 = 起始 + 60
while time.time() < 截止:
    if 程序.poll() is not None:
        print("!! 进程提前退出，退出码 %s（耗时 %.1fs）" % (程序.returncode, time.time() - 起始))
        sys.exit(1)
    窗口 = 找窗口()
    if 窗口:
        break
    time.sleep(0.4)

耗时 = time.time() - 起始
if 窗口:
    print("窗口出现：%r" % 窗口)
    print("启动耗时：%.1f 秒" % 耗时)
else:
    print("!! 等了 %.1f 秒仍没找到窗口" % 耗时)

def 杀进程树(进程):
    """结束 exe 的整棵进程树。

    单文件 exe 是「引导进程 + 应用子进程」两层，terminate() 只杀得掉
    引导进程，子进程会变成孤儿并**锁住 exe 文件**，导致下次打包失败。
    """
    try:
        subprocess.run(
            ["taskkill", "/T", "/F", "/PID", str(进程.pid)],
            capture_output=True, timeout=15,
        )
    except Exception:  # noqa: BLE001
        try:
            进程.kill()
        except Exception:  # noqa: BLE001
            pass
    try:
        进程.wait(timeout=10)
    except Exception:  # noqa: BLE001
        pass


杀进程树(程序)

# 顺手量一下内核模式（不建窗口）的启动耗时，区分是解包慢还是界面慢
起始2 = time.time()
r = subprocess.run([exe, "--内核", "--版本"], capture_output=True, timeout=120)
耗时2 = time.time() - 起始2
出 = (r.stdout or b"").decode("utf-8", "replace").strip()
print()
print("内核模式耗时：%.1f 秒（输出 %r）" % (耗时2, 出.splitlines()[0] if 出 else ""))

sys.exit(0 if 窗口 else 1)
