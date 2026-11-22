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
print("已启动 pid=%d，轮询等窗口出现…" % 程序.pid)


def 找窗口(排除标题=None):
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
        找到 = [t for t in 标题们 if "核工坊" in t]
        if 排除标题:
            找到 = [t for t in 找到 if t not in 排除标题]
        return 找到
    except Exception as e:  # noqa: BLE001
        print("查窗口失败:", e)
        return []


# 启动**之前**先记下已经开着的核工坊窗口。
#
# 为什么必须排掉它们：以前测试只按「有没有标题含核工坊的窗口」判断成功，
# 于是别处残留的孤儿进程（调试时手开的、上次测试没杀干净的）
# 会让测试**立刻通过**——实测踩过：新 exe 还在解包，测试 0.0 秒就报
# 「启动耗时 0.0 秒」「GUI exe 正常启动」，而找到的其实是 14:38 就开着的
# 一个旧版本窗口（标题写着 v0.0.13，内核已经是 0.1.4）。
# 这种「测了个假的成功」比失败更危险。
现成 = set(找窗口())
if 现成:
    print("注意：启动前已存在 %d 个核工坊窗口，将在比对时排除：%r" % (len(现成), sorted(现成)))


# 不能固定睡几秒就去找窗口：单文件 exe 要把 107MB 解包到临时目录，
# 启动本来就要 5~7 秒，机器一忙更久，固定等待会把「慢」误判成「失败」
# （0.0.12 实测 6.5 秒出现，而旧的固定等待只有 6 秒 → 假报警一次）。
目标 = []
起始 = time.time()
截止 = 起始 + 60
while time.time() < 截止:
    if 程序.poll() is not None:
        print("!! 进程提前退出，退出码 %s" % 程序.returncode)
        break
    目标 = 找窗口(排除标题=现成)
    if 目标:
        break
    time.sleep(0.4)

活着 = 程序.poll() is None
print("进程仍在运行:", 活着)
print("找到的核工坊窗口:", 目标)
if 目标:
    print("启动耗时：%.1f 秒" % (time.time() - 起始))

def 杀进程树(进程):
    """结束 exe 的**整棵进程树**。

    PyInstaller 单文件 exe 是「引导进程 + 真正跑应用的子进程」两层结构，
    `terminate()` 只杀得掉引导进程，子进程会变成孤儿：窗口还开着、
    而且**锁着 dist/核工程Qt.exe**，下一次打包就会因为无法覆盖而失败
    （实测踩过一次，误以为打包脚本坏了）。
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
码 = 程序.returncode if 程序.returncode is not None else -1
# 注意：不能在这里用 程序.stdout.read() —— 打包出来的是 console=False 的
# GUI 程序，标准输出管道不会关闭，read() 会一直等到进程结束，
# 整个测试就挂在那儿不动了（实测卡死过一次）。
# 这里直接放弃读输出：界面是否正常由「进程还活着 + 找到窗口标题」判断，
# 详细的界面自检走 --自检界面 那一路。
try:
    if 程序.stdout:
        程序.stdout.close()
except Exception:
    pass
输出 = ""
print("退出码:", 码)
if 输出:
    print("输出:", 输出[:600])

ok = 活着 and bool(目标)
print("\n结果:", "GUI exe 正常启动" if ok else "启动异常")
sys.exit(0 if ok else 1)
