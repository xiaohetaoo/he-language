# -*- coding: utf-8 -*-
"""圆角支持（Windows 原生 + Canvas 绘制），只用标准库。

三个层次：
  1. 窗口圆角：DWMWA_WINDOW_CORNER_PREFERENCE（Win11 起原生圆角）。
     Win10 及以下自动降级为直角，不影响使用。
  2. 控件圆角：用 Canvas 画圆角矩形（面板、按钮、标签页底衬）。
  3. 图片圆角：用 Pillow 给图标加圆角遮罩（有 Pillow 才做）。

非 Windows 环境下所有函数安全降级。
"""

import sys

可用 = sys.platform == "win32"

# DWM 窗口圆角偏好
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWCP_DEFAULT = 0
DWMWCP_DONOTROUND = 1
DWMWCP_ROUND = 2
DWMWCP_ROUNDSMALL = 3

# 深色标题栏（Win10 1809+ / Win11）
DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_CAPTION_COLOR = 35
DWMWA_BORDER_COLOR = 34


def _dwm():
    import ctypes

    return ctypes.WinDLL("dwmapi", use_last_error=True)


def 窗口圆角(根窗口, 偏好=DWMWCP_ROUND, 标题栏色=None, 边框色=None, 深色=True):
    """给顶层窗口设置圆角与标题栏配色。返回是否成功。

    参数里的颜色是 (r, g, b)，或 None 表示跟随系统。
    """
    if not 可用:
        return False
    try:
        import ctypes
        from ctypes import wintypes

        dwm = _dwm()
        根窗口.update_idletasks()
        user32 = ctypes.WinDLL("user32")
        user32.GetParent.argtypes = [wintypes.HWND]
        user32.GetParent.restype = wintypes.HWND
        hwnd = user32.GetParent(根窗口.winfo_id()) or 根窗口.winfo_id()
        if not hwnd:
            return False

        def _设(属性, 值):
            try:
                return dwm.DwmSetWindowAttribute(
                    wintypes.HWND(hwnd), 属性, ctypes.byref(值), ctypes.sizeof(值)
                ) == 0
            except Exception:
                return False

        成功 = _设(DWMWA_WINDOW_CORNER_PREFERENCE, ctypes.c_int(偏好))
        # 标题栏深色 / 自定义色（老系统上无效，忽略即可）
        _设(DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.c_int(1 if 深色 else 0))
        if 标题栏色 is not None:
            _设(DWMWA_CAPTION_COLOR, ctypes.c_int(_色值(标题栏色)))
        if 边框色 is not None:
            _设(DWMWA_BORDER_COLOR, ctypes.c_int(_色值(边框色)))
        return 成功
    except Exception:
        return False


def _色值(rgb):
    """(r,g,b) -> COLORREF 整数（DWM 用 0x00BBGGRR）。"""
    r, g, b = rgb
    return (b << 16) | (g << 8) | r


def hex转rgb(颜色):
    """'#rrggbb' -> (r, g, b)。"""
    颜色 = 颜色.lstrip("#")
    return (int(颜色[0:2], 16), int(颜色[2:4], 16), int(颜色[4:6], 16))


def 圆角矩形(画布, x1, y1, x2, y2, 半径, **选项):
    """在 Canvas 上画一个圆角矩形，返回 item id。

    用「直线 + 圆弧」拼出来；Tk 8.6 没有原生圆角。
    """
    半径 = max(0, min(半径, (x2 - x1) // 2, (y2 - y1) // 2))
    if 半径 <= 0:
        return 画布.create_rectangle(x1, y1, x2, y2, **选项)

    # 平滑多边形的取点技巧：在每个圆角处把点并拢，配合 smooth=True
    点 = [
        x1 + 半径, y1,
        x2 - 半径, y1,
        x2, y1,
        x2, y1 + 半径,
        x2, y2 - 半径,
        x2, y2,
        x2 - 半径, y2,
        x1 + 半径, y2,
        x1, y2,
        x1, y2 - 半径,
        x1, y1 + 半径,
        x1, y1,
    ]
    return 画布.create_polygon(点, smooth=True, splinesteps=12, **选项)


def 圆角图(路径, 边长, 半径, 背景色="#000000"):
    """把图标按圆角裁切并缩放，返回 PIL Image；没有 Pillow 时返回 None。"""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    try:
        from PIL import Image as _I

        图 = _I.open(路径).convert("RGBA")
    except Exception:
        return None
    半径 = max(0, min(int(半径), 边长 // 2))
    图.thumbnail((边长, 边长), _I.LANCZOS)
    画布 = _I.new("RGBA", (边长, 边长), (0, 0, 0, 0))
    画布.paste(图, ((边长 - 图.width) // 2, (边长 - 图.height) // 2), 图)
    if 半径 <= 0:
        return 画布
    遮罩 = _I.new("L", (边长, 边长), 0)
    ImageDraw.Draw(遮罩).rounded_rectangle(
        (0, 0, 边长 - 1, 边长 - 1), radius=半径, fill=255
    )
    结果 = _I.new("RGBA", (边长, 边长), (0, 0, 0, 0))
    结果.paste(画布, (0, 0), 遮罩)
    return 结果
