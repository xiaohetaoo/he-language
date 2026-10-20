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

    if 参数 and 参数[0] == "--自检界面":
        return _自检界面(参数[1:])

    import 核工坊

    # 显式导入一次，让 PyInstaller 的静态分析能把它打进 exe
    for 模块名 in ("拖放", "圆角", "设置窗口"):
        try:
            __import__(模块名)
        except ImportError:
            pass

    核工坊.宿主EXE = os.path.abspath(sys.executable) if getattr(sys, "frozen", False) else None
    return 核工坊.启动(参数)


def _自检界面(参数):
    """让打包后的 exe 自己截自己的图并写出自检报告。

    用法：核工坊.exe --自检界面 [输出目录]

    为什么要这么做：外部截图工具要么抓不到 DWM 绘制的标题栏
    （PrintWindow），要么会被别的窗口盖住（屏幕抓取），
    反复造成「图标/主题没生效」的误判。窗口自己截图则所见即所得。
    """
    import json
    import time

    import 核工坊

    输出目录 = 参数[0] if 参数 else os.path.dirname(os.path.abspath(sys.executable))
    os.makedirs(输出目录, exist_ok=True)

    窗口 = 核工坊.主窗口()
    根 = 窗口.根
    # 等到欢迎页图标确实加载出来（打包版冷启动较慢），否则报告会误报「无图标」
    截止 = time.time() + 10
    while time.time() < 截止:
        根.update()
        time.sleep(0.05)
        if getattr(窗口, "欢迎图", None) is not None:
            break
    for _ in range(20):
        根.update()
        time.sleep(0.02)

    # 若欢迎图缺失，直接把失败原因记进报告，便于定位（打包后没有控制台可看）
    欢迎失败 = ""
    if getattr(窗口, "欢迎图", None) is None:
        try:
            import traceback

            import tkinter as tk

            tk.PhotoImage(file=核工坊.图标PNG, master=根)
            欢迎失败 = "PhotoImage 能加载，但窗口里没有欢迎图"
        except Exception:
            欢迎失败 = "加载图标失败：" + traceback.format_exc().splitlines()[-1]

    报告 = {
        "运行方式": "打包 exe" if getattr(sys, "frozen", False) else "源码",
        "界面版本": _内核版本(),
        "配置目录": 核工坊.配置目录(),
        "默认项目目录": 核工坊.默认项目目录(),
        "实际项目目录": 窗口.项目目录,
        "工具栏": [b.文本 for b in 窗口.按钮集],
        "左条": list(窗口.左按钮),
        "有设置对话框": hasattr(窗口, "打开设置"),
        "欢迎图": getattr(窗口, "欢迎图", None) is not None,
        "图标PNG存在": os.path.exists(核工坊.图标PNG),
        "欢迎失败原因": 欢迎失败,
        "主题": 窗口.主题["名"],
    }

    # 逐个主题截图：窗口自己抓自己，不受其它窗口影响
    图集 = {}
    for 主题名 in ("深色", "浅色"):
        窗口.换主题(主题名)
        # 换主题会重建控件，先充分刷新到布局稳定，再交给 _截自己
        for _ in range(60):
            根.update()
            time.sleep(0.03)
        time.sleep(0.4)
        路径 = os.path.join(输出目录, "自检_%s.png" % 主题名)
        图集[主题名] = _截自己(窗口, 路径)

    报告["截图"] = 图集
    with open(os.path.join(输出目录, "自检报告.json"), "w", encoding="utf-8") as f:
        json.dump(报告, f, ensure_ascii=False, indent=2)

    print("自检报告已写入：%s" % os.path.join(输出目录, "自检报告.json"))
    print(json.dumps(报告, ensure_ascii=False, indent=2))
    窗口.销毁()
    return 0


def _截自己(窗口, 输出):
    """在窗口自己的进程里截图。

    先把窗口移到屏幕左上角，再用 PrintWindow 抓；PrintWindow 对
    普通控件足够，配合窗口自绘的标题栏，能反映真实观感。
    """
    import ctypes
    import time
    from ctypes import wintypes

    根 = 窗口.根
    try:
        u = ctypes.windll.user32
        u.SetWindowPos.argtypes = [
            wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
            ctypes.c_int, ctypes.c_int, ctypes.c_uint,
        ]
        根.attributes("-topmost", True)
        根.geometry("+0+0")
        根.update()
        句柄 = u.GetParent(根.winfo_id())
        # 必须带 SWP_NOSIZE，否则 SetWindowPos 会把窗口缩到最小尺寸（曾经截出 144x40）
        u.SetWindowPos(
            wintypes.HWND(句柄), wintypes.HWND(-1), 0, 0, 0, 0, 0x0001 | 0x0040
        )
        u.SetForegroundWindow(句柄)
        # 等窗口确实完成布局：尺寸稳定下来再截，否则会截到 144x40 这种半成品
        上次 = None
        for _ in range(80):
            根.update()
            time.sleep(0.05)
            矩形 = wintypes.RECT()
            u.GetWindowRect(句柄, ctypes.byref(矩形))
            现在 = (矩形.right - 矩形.left, 矩形.bottom - 矩形.top)
            if 现在 == 上次 and 现在[0] > 300 and 现在[1] > 300:
                break
            上次 = 现在

        矩形 = wintypes.RECT()
        u.GetWindowRect(句柄, ctypes.byref(矩形))
        宽 = 矩形.right - 矩形.left
        高 = 矩形.bottom - 矩形.top

        from PIL import Image

        屏幕 = u.GetWindowDC(句柄)
        内存 = ctypes.windll.gdi32.CreateCompatibleDC(屏幕)
        位图 = ctypes.windll.gdi32.CreateCompatibleBitmap(屏幕, 宽, 高)
        ctypes.windll.gdi32.SelectObject(内存, 位图)
        u.PrintWindow(句柄, 内存, 2)

        class 头(ctypes.Structure):
            _fields_ = [
                ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD),
            ]

        信息 = 头()
        信息.biSize = ctypes.sizeof(头)
        信息.biWidth = 宽
        信息.biHeight = -高
        信息.biPlanes = 1
        信息.biBitCount = 32
        缓冲 = ctypes.create_string_buffer(宽 * 高 * 4)
        ctypes.windll.gdi32.GetDIBits(内存, 位图, 0, 高, 缓冲, ctypes.byref(信息), 0)
        Image.frombuffer(
            "RGBA", (宽, 高), 缓冲, "raw", "BGRA", 0, 1
        ).convert("RGB").save(输出)
        根.attributes("-topmost", False)
        return {"路径": 输出, "宽": 宽, "高": 高}
    except Exception as e:  # noqa: BLE001
        return {"错误": "%s: %s" % (type(e).__name__, e)}


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


def _内核版本():
    try:
        import 核

        return 核.版本
    except Exception:  # noqa: BLE001
        return "未知"


def 基目录():
    return _资源目录()


if __name__ == "__main__":
    sys.exit(主())
