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

# ctypes / wintypes 必须在**模块级**导入。
# 以前只在 _准备() 里局部 import，而 释放拖放() 直接写了 ctypes.WinDLL ——
# 那里根本没有这个名字，每次都抛 NameError 被自己的 except 吞掉，
# 于是「释放」永远什么都没做，模块级容器只增不减（实测调完仍在）。
if 可用:
    import ctypes
    from ctypes import wintypes
else:                      # 非 Windows：留个占位，调用方一律先判 可用
    ctypes = None
    wintypes = None

WM_DROPFILES = 0x0233
GWL_WNDPROC = -4

# 回调保存在模块级，防止被 GC 回收后窗口过程指向已释放的函数。
# **按句柄存**：只有把窗口过程真正还原回去之后，才允许丢掉对应那一个。
_回调引用 = {}
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

    # 这里**不再**调 释放拖放(全部=True)。
    # 以前那么写：它把别的窗口的原过程指针和回调引用一起清空，
    # 可那些窗口的窗口过程**还指着我们的回调** —— 回调对象一被回收，
    # 下一条消息就打到已释放的函数指针上（进程级崩溃）；就算没崩，
    # _原过程.get(句柄) 也只剩 None，转发同样要炸。
    # 上面那句「句柄已启用就直接返回」保证了这里不会重复挂钩子，
    # 别的窗口的状态原样留着，各自销毁时由 释放拖放 单独撤掉。
    _原过程[句柄] = ctypes.cast(原, ctypes.c_void_p) if 原 else None
    _回调引用[句柄] = 新过程
    _已启用.add(句柄)
    return True


def _撤掉(句柄, shell32=None, 设过程=None):
    """把一个窗口恢复成启用拖放之前的样子，再丢掉它的引用。

    顺序很重要：**先还原窗口过程，后丢回调引用**。反过来的话，
    窗口过程还指着我们刚释放掉的函数，下一条消息就是野指针。
    """
    原 = _原过程.pop(句柄, None)
    _已启用.discard(句柄)
    if 原 is not None and 设过程 is not None:
        try:
            设过程(句柄, GWL_WNDPROC, 原)
        except Exception as e:  # noqa: BLE001
            _记录("还原窗口过程失败：%s" % e)
    if shell32 is not None:
        try:
            shell32.DragAcceptFiles(句柄, False)
        except Exception as e:  # noqa: BLE001
            _记录("关闭拖放失败：%s" % e)
    # 到这里窗口已经不再指向我们的回调，丢掉它才是安全的
    _回调引用.pop(句柄, None)


def 释放拖放(根窗口=None, 全部=False):
    """窗口销毁时调用：还原窗口过程并清掉引用，避免容器无限增长。"""
    if not 可用:
        return
    if 全部:
        try:
            _ctypes, _wintypes, _user32, shell32, 设过程 = _准备()
        except Exception:  # noqa: BLE001
            shell32 = 设过程 = None
        for 句柄 in list(_已启用):
            _撤掉(句柄, shell32, 设过程)
        _原过程.clear()
        _已启用.clear()
        _回调引用.clear()
        return
    if 根窗口 is None:
        return
    try:
        _ctypes, _wintypes, user32, shell32, 设过程 = _准备()
        子句柄 = 根窗口.winfo_id()
        句柄 = user32.GetParent(子句柄) or 子句柄
    except Exception:  # noqa: BLE001
        return
    _撤掉(句柄, shell32, 设过程)
