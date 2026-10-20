# -*- coding: utf-8 -*-
"""给 Tk 窗口加上「把文件拖进来」的能力（Windows 原生，只用标准库 ctypes）。

原理：
  1. DragAcceptFiles(hwnd, True) 让窗口接受拖放；
  2. 用 SetWindowLongPtrW 替换窗口过程，截获 WM_DROPFILES；
  3. 从 HDROP 里取出被拖入的文件路径，交给回调；
  4. 其余消息原样转给原来的窗口过程。

非 Windows、或任何一步失败时静默降级：界面照常使用，只是不能拖放。
"""

import sys

可用 = sys.platform == "win32"

WM_DROPFILES = 0x0233
GWL_WNDPROC = -4

# 回调保存在模块级，防止被 GC 回收后窗口过程指向已释放的函数
_回调引用 = []
_原过程 = {}
_已启用 = set()
_日志 = []


def _记录(文本):
    _日志.append(文本)
    if len(_日志) > 50:
        del _日志[0]


def _准备():
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    shell32 = ctypes.WinDLL("shell32", use_last_error=True)

    shell32.DragAcceptFiles.argtypes = [wintypes.HWND, wintypes.BOOL]
    shell32.DragAcceptFiles.restype = None
    shell32.DragQueryFileW.argtypes = [
        wintypes.HANDLE,
        wintypes.UINT,
        wintypes.LPWSTR,
        wintypes.UINT,
    ]
    shell32.DragQueryFileW.restype = wintypes.UINT
    shell32.DragFinish.argtypes = [wintypes.HANDLE]
    shell32.DragFinish.restype = None
    user32.CallWindowProcW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT,
                                       wintypes.WPARAM, wintypes.LPARAM]
    user32.CallWindowProcW.restype = ctypes.c_ssize_t
    user32.GetParent.argtypes = [wintypes.HWND]
    user32.GetParent.restype = wintypes.HWND

    if ctypes.sizeof(ctypes.c_void_p) == 8:
        user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
        user32.SetWindowLongPtrW.restype = ctypes.c_void_p
        设过程 = user32.SetWindowLongPtrW
    else:
        user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
        user32.SetWindowLongW.restype = ctypes.c_void_p
        设过程 = user32.SetWindowLongW

    return ctypes, wintypes, user32, shell32, 设过程


def 取拖入路径(HDROP):
    """从 HDROP 句柄解析出文件路径列表（供测试直接调用）。"""
    if not 可用:
        return []
    ctypes, wintypes, _user32, shell32, _ = _准备()
    数目 = shell32.DragQueryFileW(HDROP, 0xFFFFFFFF, None, 0)
    结果 = []
    for i in range(数目):
        长度 = shell32.DragQueryFileW(HDROP, i, None, 0)
        if 长度 <= 0:
            continue
        缓冲 = ctypes.create_unicode_buffer(长度 + 1)
        shell32.DragQueryFileW(HDROP, i, 缓冲, 长度 + 1)
        结果.append(缓冲.value)
    return 结果


def 启用拖放(根窗口, 回调, 失败提示=None):
    """让 根窗口 接受文件拖放；拖入时调用 回调([路径, ...])。

    返回 True 表示启用成功。
    """
    if not 可用:
        return False
    try:
        ctypes, wintypes, user32, shell32, 设过程 = _准备()
    except Exception as e:  # noqa: BLE001
        if 失败提示:
            失败提示("拖放不可用：%s" % e)
        return False

    try:
        根窗口.update_idletasks()
        子句柄 = 根窗口.winfo_id()
        # Tk 的 winfo_id() 可能是子窗口，真正的顶层由 GetParent 给出；
        # 某些情况下 GetParent 返回 0/None，这时就用 winfo_id() 本身。
        句柄 = user32.GetParent(子句柄) or 子句柄
        if not 句柄:
            句柄 = 子句柄
        if 句柄 in _已启用:
            return True
    except Exception:
        return False

    shell32.DragAcceptFiles(句柄, True)

    WNDPROC = ctypes.WINFUNCTYPE(
        ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
    )

    def _过程(hwnd, msg, wparam, lparam):
        try:
            if msg == WM_DROPFILES:
                路径集 = 取拖入路径(wparam)
                shell32.DragFinish(wparam)
                if 路径集:
                    根窗口.after(0, lambda: 回调(路径集))
                return 0
        except Exception as e:  # noqa: BLE001
            _记录("处理拖放失败：%s" % e)
        try:
            return user32.CallWindowProcW(_原过程.get(句柄), hwnd, msg, wparam, lparam)
        except Exception as e:  # noqa: BLE001
            _记录("转发消息失败：%s" % e)
            return 0

    新过程 = WNDPROC(_过程)
    try:
        import ctypes as _c

        原 = 设过程(句柄, GWL_WNDPROC, _c.cast(新过程, _c.c_void_p))
    except Exception as e:  # noqa: BLE001
        if 失败提示:
            失败提示("拖放不可用：%s" % e)
        return False

    _原过程[句柄] = ctypes.cast(原, ctypes.c_void_p) if 原 else None
    _回调引用.append(新过程)
    _已启用.add(句柄)
    return True
