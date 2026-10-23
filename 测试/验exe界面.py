# -*- coding: utf-8 -*-
"""启动打包好的 exe（GUI 模式），确认真的能起来、窗口显示、然后优雅关闭。"""
import os
import subprocess
import sys
import time

这里 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
exe = os.path.join(这里, "dist", "核工坊Qt.exe")

程序 = subprocess.Popen([exe], cwd=这里,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
print("已启动 pid=%d，等 6 秒让它把界面画出来…" % 程序.pid)
time.sleep(6)

活着 = 程序.poll() is None
print("进程仍在运行:", 活着)

# 抓一下窗口标题，确认真的建了窗口
try:
    import ctypes
    from ctypes import wintypes

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
    目标 = [t for t in 标题们 if "核工坊" in t]
    print("找到的核工坊窗口:", 目标)
except Exception as e:  # noqa: BLE001
    print("查窗口失败:", e)
    目标 = []

程序.terminate()
try:
    码 = 程序.wait(timeout=10)
except subprocess.TimeoutExpired:
    程序.kill()
    码 = 程序.wait()
输出 = (程序.stdout.read() or b"").decode("utf-8", "replace").strip()
print("退出码:", 码)
if 输出:
    print("输出:", 输出[:600])

ok = 活着 and bool(目标)
print("\n结果:", "GUI exe 正常启动" if ok else "启动异常")
sys.exit(0 if ok else 1)
