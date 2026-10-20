# -*- coding: utf-8 -*-
"""拍一张核工坊的界面截图，用于说明文档。

用法：python 测试/拍图.py [输出文件]
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

import 核工坊 as 工坊  # noqa: E402

示例 = os.path.join(根目录, "例子", "03_容器与函数.xht")


def 拍(输出, 文件=None, 浅色=False, 欢迎页=False):
    from PIL import ImageGrab

    窗口 = 工坊.主窗口()
    根 = 窗口.根
    根.update()
    窗口.最近 = [示例]
    if 浅色:
        窗口.换主题("浅色")
    窗口.对照变量.set(True)
    窗口._显示对照表()
    if 欢迎页:
        根.update()
        for d in list(窗口.文档集):
            窗口.关闭文档(d, 强制=True)
        窗口._显示欢迎()
        根.update()
        return _抓图(根, 输出)
    目标 = 文件 or 示例
    窗口.打开(目标)
    根.update()
    窗口.运行()
    for _ in range(200):
        根.update()
        time.sleep(0.02)
        if 窗口.进程 is None:
            break
    根.update()
    尺寸 = _抓图(根, 输出)
    根.destroy()
    return 尺寸


def _抓图(根, 输出):
    from PIL import ImageGrab

    hwnd = ctypes.windll.user32.GetParent(根.winfo_id())
    ctypes.windll.user32.ShowWindow(hwnd, 9)
    根.lift()
    根.attributes("-topmost", True)
    for _ in range(10):
        根.update()
        time.sleep(0.06)
    r = wintypes.RECT()
    ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(r), ctypes.sizeof(r))
    图 = ImageGrab.grab(bbox=(r.left, r.top, r.right, r.bottom))
    图.save(输出)
    return 图.size


if __name__ == "__main__":
    参数 = [a for a in sys.argv[1:] if not a.startswith("--")]
    目标 = 参数[0] if 参数 else os.path.join(根目录, "截图_核工坊.png")
    浅 = "--浅色" in sys.argv
    欢 = "--欢迎页" in sys.argv
    # 主窗口会自己扫描 sys.argv 找待打开文件，这里先清掉，免得把输出图片也打开
    sys.argv = sys.argv[:1]
    print(拍(目标, 浅色=浅, 欢迎页=欢))
