# -*- coding: utf-8 -*-
"""生成核工坊界面截图。

用法：
    python 测试/截图.py                       核核 全部重拍（主界面 / 浅色 / 欢迎页 / 设置）
    python 测试/截图.py 截图_核工坊.png        核核 只拍主界面
    python 测试/截图.py --浅色                核核 拍浅色主题
    python 测试/截图.py --欢迎页              核核 拍欢迎页
    python 测试/截图.py --设置                核核 拍设置窗口

抓图方式说明
------------
之前试过两种方式都有坑：
  · PrintWindow 抓不到 DWM 绘制的标题栏（图标、圆角会缺失）
  · DWM 边界 + ImageGrab 会被别的窗口盖住

这里用「把窗口移到左上角并强制置顶，再从桌面截取固定区域」，
所见即所得：标题栏图标、圆角、配色都能正确呈现。
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

from PIL import ImageGrab  # noqa: E402


def _找窗口(前缀="核工坊", 超时=20):
    u = ctypes.windll.user32
    u.GetParent.argtypes = [wintypes.HWND]
    u.GetParent.restype = wintypes.HWND
    截止 = time.time() + 超时
    while time.time() < 截止:
        找到 = []

        def 回调(h, _l):
            长度 = u.GetWindowTextLengthW(h)
            if 长度 <= 0:
                return True
            名 = ctypes.create_unicode_buffer(长度 + 1)
            u.GetWindowTextW(h, 名, 长度 + 1)
            if 名.value.startswith(前缀) and u.IsWindowVisible(h):
                找到.append(h)
            return True

        u.EnumWindows(
            ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)(回调), 0
        )
        if 找到:
            return 找到[0]
        time.sleep(0.4)
    return None


def _窗口大小(句柄):
    r = wintypes.RECT()
    ctypes.windll.dwmapi.DwmGetWindowAttribute(
        句柄, 9, ctypes.byref(r), ctypes.sizeof(r)
    )
    宽 = r.right - r.left
    高 = r.bottom - r.top
    if 宽 < 100 or 高 < 100:
        u = ctypes.windll.user32
        u.GetWindowRect(句柄, ctypes.byref(r))
        宽 = r.right - r.left
        高 = r.bottom - r.top
    return 宽, 高


def _抓(句柄, 输出, 边距=40, 根=None):
    """把窗口摆到左上角并置顶，然后从桌面截取，保证不被遮挡。

    思路：Tk 的 -topmost 属性最可靠（比 SetWindowPos 更能抢回焦点）。
    摆好后先验证窗口确实在 (0,0) 且在最前，再截图。
    """
    u = ctypes.windll.user32
    u.SetWindowPos.argtypes = [
        wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, ctypes.c_int, ctypes.c_uint,
    ]
    u.GetParent.argtypes = [wintypes.HWND]
    u.GetParent.restype = wintypes.HWND

    # 先最小化再还原：这样窗口会回到 Z 序最前，旁边不会露出别的窗口
    # （曾出现截图左边缘混进一条别人的窗口）。
    if 根 is not None:
        try:
            根.iconify()
            根.update()
            time.sleep(0.3)
            根.deiconify()
            根.update()
        except Exception:  # noqa: BLE001
            pass

    宽, 高 = _窗口大小(句柄)

    for _ in range(8):
        if 根 is not None:
            try:
                根.attributes("-topmost", True)
                根.geometry("+0+0")
                根.deiconify()
                根.lift()
                根.update()
            except Exception:
                pass
        u.SetWindowPos(wintypes.HWND(句柄), wintypes.HWND(-1), 0, 0, 0, 0,
                       0x0001 | 0x0040)
        u.SetForegroundWindow(句柄)
        time.sleep(0.35)
        r = wintypes.RECT()
        u.GetWindowRect(句柄, ctypes.byref(r))
        if r.left <= 2 and r.top <= 2:
            break
    time.sleep(0.9)

    # 尺寸必须等到稳定再取：切主题/建控件会让窗口短时间内缩到最小尺寸，
    # 若沿用开头的旧值或就着当时的尺寸裁剪，会截出 237x39 这种碎片。
    上次 = (宽, 高)
    稳定 = 0
    for _ in range(60):
        r = wintypes.RECT()
        u.GetWindowRect(句柄, ctypes.byref(r))
        现在 = (r.right - r.left, r.bottom - r.top)
        if 现在 == 上次 and 现在[0] > 400 and 现在[1] > 300:
            稳定 += 1
            if 稳定 >= 3:
                break
        else:
            稳定 = 0
        上次 = 现在
        time.sleep(0.05)
    宽, 高 = 上次

    r = wintypes.RECT()
    u.GetWindowRect(句柄, ctypes.byref(r))
    右 = min(r.right, r.left + 宽)
    下 = min(r.bottom, r.top + 高)
    图 = ImageGrab.grab(bbox=(r.left, r.top, 右, 下), all_screens=True)
    图.save(输出)
    if 根 is not None:
        try:
            根.attributes("-topmost", False)
        except Exception:
            pass
    return 图.size


def 拍(输出=None, 浅色=False, 欢迎页=False, 设置=False, 对照表=True, 运行=False):
    sys.argv = [sys.argv[0]]
    import 核工坊

    输出 = 输出 or os.path.join(根目录, "截图_核工坊.png")
    窗口 = 核工坊.主窗口()
    根 = 窗口.根
    for _ in range(30):
        根.update()
        time.sleep(0.02)

    if 浅色:
        窗口.换主题("浅色")
    if 对照表 and not 设置:
        窗口.对照变量.set(True)
        窗口._显示对照表()

    if 欢迎页:
        for 文档 in list(窗口.文档集):
            窗口.关闭文档(文档, 强制=True)
        窗口._显示欢迎()
    elif not 设置:
        窗口.打开(os.path.join(根目录, "例子", "03_容器与函数.xht"))
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

    句柄 = ctypes.windll.user32.GetParent(根.winfo_id())
    尺寸 = _抓(句柄, 输出, 根=根)

    if 设置:
        import 设置窗口

        窗 = 设置窗口.设置窗口(窗口)
        窗.geometry("+120+80")
        for _ in range(30):
            根.update()
            time.sleep(0.03)
        句柄2 = ctypes.windll.user32.GetParent(窗.winfo_id())
        _抓(句柄2, os.path.join(根目录, "截图_设置.png"), 边距=10, 根=窗)
        if 窗.winfo_exists():
            窗.销毁()

    窗口.销毁()
    return 尺寸


if __name__ == "__main__":
    参数 = [a for a in sys.argv[1:] if not a.startswith("--")]
    指定 = 参数[0] if 参数 else None
    浅 = "--浅色" in sys.argv
    欢迎 = "--欢迎页" in sys.argv
    设置 = "--设置" in sys.argv
    运行 = "--运行" in sys.argv

    if 指定 and not (浅 or 欢迎 or 设置):
        # 只拍一张
        print(拍(指定, 运行=运行))
    else:
        if 设置:
            print("设置窗口：", 拍(os.path.join(根目录, "截图_核工坊.png"), 设置=True, 对照表=False))
            print("主界面：", 拍(os.path.join(根目录, "截图_核工坊.png"), 运行=True))
        else:
            print("主界面：", 拍(os.path.join(根目录, "截图_核工坊.png"), 运行=True))
            print("浅色：", 拍(os.path.join(根目录, "截图_核工坊_浅色.png"), 浅色=True, 运行=True))
            print("欢迎页：", 拍(os.path.join(根目录, "截图_欢迎页.png"), 欢迎页=True))
