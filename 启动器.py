# -*- coding: utf-8 -*-
"""核工坊 打包入口（同时充当内核解释器）。

两种身份：
  1. 双击 / 无参数      → 打开图形界面
  2. 核工坊.exe --内核 文件.xht
     → 不打开界面，直接在进程内转译并执行 .xht，行为等同 `python 核.py 文件.xht`

第 2 种身份是打包版的关键：exe 里已经内置了 核.py，运行用户程序时
就重新调用自己，因此**不需要目标机器安装 Python**。
"""

import os
import sys


def _资源目录():
    """PyInstaller 单文件模式下，资源被解到 sys._MEIPASS。"""
    基 = getattr(sys, "_MEIPASS", None)
    if 基:
        return 基
    return os.path.dirname(os.path.abspath(__file__))


def 准备路径():
    基 = _资源目录()
    for 子 in ("", "素材", "例子"):
        目录 = os.path.join(基, 子) if 子 else 基
        if os.path.isdir(目录) and 目录 not in sys.path:
            sys.path.insert(0, 目录)
    return 基


#: 作为内核被调用时使用的参数名。
内核参数 = "--内核"

#: 内核被调用时，告诉 核工坊 用哪种方式宿主运行。
环境标记 = "核_EXE_内核"


def 主():
    基 = 准备路径()
    参数 = sys.argv[1:]

    if 参数 and 参数[0] == 内核参数:
        import 核

        return 核.命令行(参数[1:])

    if 参数 and 参数[0] == "--自检":
        return _自检拖放()

    import 核工坊

    # 显式导入一次，让 PyInstaller 的静态分析能把它打进 exe
    for 模块名 in ("拖放", "圆角", "设置窗口"):
        try:
            __import__(模块名)
        except ImportError:
            pass

    核工坊.宿主EXE = os.path.abspath(sys.executable) if getattr(sys, "frozen", False) else None
    return 核工坊.启动(参数)


def _自检拖放():
    """在进程内模拟一次文件拖入，验证拖放链路是否打通（打包后也可用）。

    用法：核工坊.exe --自检 <某个.xht 路径>
    """
    import ctypes
    import time
    from ctypes import wintypes

    import 核工坊

    class DROPFILES(ctypes.Structure):
        _fields_ = [
            ("pFiles", wintypes.DWORD),
            ("pt", wintypes.POINT),
            ("fNC", wintypes.BOOL),
            ("fWide", wintypes.BOOL),
        ]

    窗口 = 核工坊.主窗口()
    根 = 窗口.根
    for _ in range(40):
        根.update()
        time.sleep(0.02)

    目标 = sys.argv[2] if len(sys.argv) > 2 else os.path.join(基目录(), "例子", "02_条件与循环.xht")

    u = ctypes.WinDLL("user32")
    k = ctypes.WinDLL("kernel32")
    u.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    k.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    k.GlobalAlloc.restype = ctypes.c_void_p
    k.GlobalLock.argtypes = [ctypes.c_void_p]
    k.GlobalLock.restype = ctypes.c_void_p

    尺寸 = ctypes.sizeof(DROPFILES)
    头 = ctypes.create_string_buffer(尺寸)
    ctypes.memmove(头, ctypes.byref(DROPFILES(pFiles=尺寸, fWide=1)), 尺寸)
    块 = 头.raw + 目标.encode("utf-16-le") + b"\x00\x00"
    句柄 = k.GlobalAlloc(0x0042, len(块))
    指针 = k.GlobalLock(句柄)
    ctypes.memmove(指针, 块, len(块))

    前 = len(窗口.文档集)
    u.SendMessageW(u.GetParent(根.winfo_id()), 0x0233, wintypes.WPARAM(句柄), 0)
    for _ in range(200):
        根.update()
        time.sleep(0.02)
        if len(窗口.文档集) > 前:
            break
    成功 = len(窗口.文档集) > 前
    print("拖放自检：%s" % ("通过" if 成功 else "失败"))
    print("  目标：%s" % 目标)
    print("  打开后文档数：%d" % len(窗口.文档集))
    根.destroy()
    return 0 if 成功 else 1


def 基目录():
    return _资源目录()


if __name__ == "__main__":
    sys.exit(主())
