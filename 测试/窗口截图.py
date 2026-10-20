# -*- coding: utf-8 -*-
"""离屏截图：直接抓取 Tk 窗口内容，不受其他窗口遮挡。

用法：python 测试/窗口截图.py <输出.png> [--打开 文件] [--运行]
"""

import ctypes
import os
import sys
import time
from ctypes import wintypes

这里 = os.path.dirname(os.path.abspath(__file__))
根目录 = os.path.dirname(这里)
sys.path.insert(0, 根目录)

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

from PIL import Image  # noqa: E402


class 位图信息(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


def 抓窗口(hwnd):
    """用 PrintWindow 抓窗口内容，返回 PIL Image。"""
    u = ctypes.windll.user32
    g = ctypes.windll.gdi32
    r = wintypes.RECT()
    u.GetWindowRect(hwnd, ctypes.byref(r))
    宽 = r.right - r.left
    高 = r.bottom - r.top
    hdc = u.GetWindowDC(hwnd)
    mdc = g.CreateCompatibleDC(hdc)
    bmp = g.CreateCompatibleBitmap(hdc, 宽, 高)
    g.SelectObject(mdc, bmp)
    u.PrintWindow(hwnd, mdc, 2)
    bi = 位图信息()
    bi.biSize = ctypes.sizeof(位图信息)
    bi.biWidth = 宽
    bi.biHeight = -高
    bi.biPlanes = 1
    bi.biBitCount = 32
    缓冲 = ctypes.create_string_buffer(宽 * 高 * 4)
    g.GetDIBits(mdc, bmp, 0, 高, 缓冲, ctypes.byref(bi), 0)
    g.DeleteObject(bmp)
    g.DeleteDC(mdc)
    u.ReleaseDC(hwnd, hdc)
    return Image.frombuffer("RGBA", (宽, 高), 缓冲, "raw", "BGRA", 0, 1).convert("RGB")


def 截取(输出, 打开=None, 运行=False, 等待=0.6):
    sys.argv = [sys.argv[0]]
    import 核工坊 as 工坊

    窗口 = 工坊.主窗口()
    根 = 窗口.根
    for _ in range(20):
        根.update()
        time.sleep(0.02)
    if 打开:
        窗口.打开(打开)
        for _ in range(20):
            根.update()
            time.sleep(0.02)
    if 运行:
        窗口.运行()
        for _ in range(200):
            根.update()
            time.sleep(0.02)
            if 窗口.进程 is None:
                break
    for _ in range(20):
        根.update()
        time.sleep(0.03)
    hwnd = ctypes.windll.user32.GetParent(根.winfo_id())
    图 = 抓窗口(hwnd)
    图.save(输出)
    窗口.销毁()
    return 图.size


if __name__ == "__main__":
    参数 = [a for a in sys.argv[1:] if not a.startswith("--")]
    输出 = 参数[0] if 参数 else os.path.join(根目录, "截图_圆角.png")
    打开 = None
    if "--打开" in sys.argv:
        打开 = sys.argv[sys.argv.index("--打开") + 1]
    print(截取(输出, 打开=打开, 运行="--运行" in sys.argv))
