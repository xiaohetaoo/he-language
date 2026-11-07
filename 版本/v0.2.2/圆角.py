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

# 窗口样式索引（GetWindowLongW / SetWindowLongW 的第二个参数）
GWL_STYLE = -16


def _dwm():
    import ctypes

    return ctypes.WinDLL("dwmapi", use_last_error=True)


def 隐藏标题栏(根窗口):
    """去掉 Windows 原生标题栏，但保留边框、阴影、贴边吸附与缩放能力。

    做法：把窗口样式从 WS_CAPTION 改成 WS_POPUP|WS_THICKFRAME，
    再给客户区加 WS_CAPTION 的「视觉边框」以保住阴影。
    overrideredirect 那种做法会连缩放和阴影一起丢掉，所以不用它。
    返回是否成功。
    """
    if not 可用:
        return False
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32")
        user32.GetParent.argtypes = [wintypes.HWND]
        user32.GetParent.restype = wintypes.HWND
        if ctypes.sizeof(ctypes.c_void_p) == 8:
            user32.GetWindowLongW.restype = ctypes.c_long
            user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
            user32.SetWindowLongW.restype = ctypes.c_long
            user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
        else:
            user32.GetWindowLongW.restype = ctypes.c_long
            user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
            user32.SetWindowLongW.restype = ctypes.c_long
            user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]

        根窗口.update_idletasks()
        hwnd = user32.GetParent(根窗口.winfo_id()) or 根窗口.winfo_id()
        样式 = user32.GetWindowLongW(hwnd, GWL_STYLE)

        WS_CAPTION = 0x00C00000
        WS_THICKFRAME = 0x00040000
        WS_SYSMENU = 0x00080000
        WS_MINIMIZEBOX = 0x00020000
        WS_MAXIMIZEBOX = 0x00010000
        WS_POPUP = 0x80000000

        # 去掉原生标题栏，但保留可缩放 + 系统菜单（Alt+Space 仍可用）
        新样式 = 样式 & ~WS_CAPTION
        新样式 |= WS_THICKFRAME | WS_SYSMENU | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_POPUP
        user32.SetWindowLongW(hwnd, GWL_STYLE, 新样式)

        # 关键：让 DWM 仍然给它画边框与阴影（否则窗口像个无边框方块）
        MARGINS = ctypes.c_int * 4
        边距 = MARGINS(-1, -1, -1, -1)
        try:
            _dwm().DwmExtendFrameIntoClientArea(wintypes.HWND(hwnd), ctypes.byref(边距))
        except Exception:
            pass

        # 让新样式生效
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOZORDER = 0x0004
        SWP_FRAMECHANGED = 0x0020
        user32.SetWindowPos(
            wintypes.HWND(hwnd), None, 0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED,
        )
        return True
    except Exception:
        return False



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
