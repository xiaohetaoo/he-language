# -*- coding: utf-8 -*-
"""把窗口的小图标画出来，确证标题栏/任务栏用的到底是哪个图标。

截图会被其他窗口遮挡、且 DWM 标题栏不经 PrintWindow 输出，
所以这里直接读窗口类图标句柄，用 DrawIconEx 画到内存位图上，
再存成 PNG —— 画出来是什么，标题栏显示的就是什么。
"""

import ctypes
import os
import sys
from ctypes import wintypes

这里 = os.path.dirname(os.path.abspath(__file__))
根目录 = os.path.dirname(这里)


def 取类图标(句柄, 大小=True):
    """读窗口类图标；大小图标分别对应 GCLP_HICONSM / GCLP_HICON。"""
    u = ctypes.windll.user32
    if ctypes.sizeof(ctypes.c_void_p) == 8:
        u.GetClassLongPtrW.restype = ctypes.c_void_p
        u.GetClassLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
        取 = u.GetClassLongPtrW
        小, 大 = -34, -14
    else:
        u.GetClassLongW.restype = ctypes.c_void_p
        u.GetClassLongW.argtypes = [wintypes.HWND, ctypes.c_int]
        取 = u.GetClassLongW
        小, 大 = -34, -14
    return 取(句柄, 小 if 大小 else 大)


def 画图标(句柄, 输出, 边长=64):
    u = ctypes.windll.user32
    g = ctypes.windll.gdi32
    图标 = 取类图标(句柄)
    if not 图标:
        print("没有类图标")
        return False

    # 建一个 32 位 DIB
    class BITMAPINFOHEADER(ctypes.Structure):
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

    class BITMAPINFO(ctypes.Structure):
        _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]

    hdc = u.GetDC(0)
    mdc = g.CreateCompatibleDC(hdc)
    bmp = g.CreateCompatibleBitmap(hdc, 边长, 边长)
    g.SelectObject(mdc, bmp)
    # 先刷白底，看清图标轮廓
    brush = g.CreateSolidBrush(0x00FFFFFF)
    rect = wintypes.RECT(0, 0, 边长, 边长)
    u.FillRect(mdc, ctypes.byref(rect), brush)
    g.DeleteObject(brush)
    # DI_NORMAL = 3
    u.DrawIconEx(mdc, 4, 4, ctypes.c_void_p(图标), 边长 - 8, 边长 - 8, 0, 0, 3)

    bi = BITMAPINFO()
    bi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bi.bmiHeader.biWidth = 边长
    bi.bmiHeader.biHeight = -边长
    bi.bmiHeader.biPlanes = 1
    bi.bmiHeader.biBitCount = 32
    缓冲 = ctypes.create_string_buffer(边长 * 边长 * 4)
    g.GetDIBits(mdc, bmp, 0, 边长, 缓冲, ctypes.byref(bi), 0)

    from PIL import Image

    Image.frombuffer("RGBA", (边长, 边长), 缓冲, "raw", "BGRA", 0, 1).convert("RGB").save(输出)
    g.DeleteObject(bmp)
    g.DeleteDC(mdc)
    u.ReleaseDC(0, hdc)
    return True


if __name__ == "__main__":
    # 自检：建窗口 → 读图标 → 设置图标 → 再读，对比句柄与图像
    import tkinter as tk
    import importlib.util

    spec = importlib.util.spec_from_file_location("核工坊", os.path.join(根目录, "核工坊.py"))
    工坊 = importlib.util.module_from_spec(spec)
    sys.modules["核工坊"] = 工坊
    spec.loader.exec_module(工坊)

    根 = tk.Tk()
    根.title("图标自检")
    根.geometry("300x200")
    根.update()
    根.deiconify()
    根.update()

    句柄 = ctypes.windll.user32.GetParent(根.winfo_id())
    前 = 取类图标(句柄)
    print("设置前 类图标句柄:", 前)
    画图标(句柄, os.path.join(根目录, "_图标_前.png"))

    工坊.设窗口图标(根)
    根.update()
    后 = 取类图标(句柄)
    print("设置后 类图标句柄:", 后)
    画图标(句柄, os.path.join(根目录, "_图标_后.png"))
    print("句柄是否改变:", 前 != 后)

    根.destroy()
