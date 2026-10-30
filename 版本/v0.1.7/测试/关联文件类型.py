# -*- coding: utf-8 -*-
"""把 .xht 文件关联到核语言（仅当前用户，不需要管理员权限）。

用法：
    python 测试/关联文件类型.py          注册关联（双击 .xht 用 核工坊 打开）
    python 测试/关联文件类型.py --查看   只看当前关联
    python 测试/关联文件类型.py --取消   删除关联

注册表位置（HKEY_CURRENT_USER\\Software\\Classes），只影响当前用户；
不写系统级关联，也不会改默认程序之外的设置。
"""

import os
import subprocess
import sys

这里 = os.path.dirname(os.path.abspath(__file__))
根目录 = os.path.dirname(这里)
类名 = "核语言.源文件"
扩展名 = ".xht"
图标 = os.path.join(根目录, "素材", "核图标.ico")
描述 = "核语言源文件"


def _打开程序():
    """优先用 Qt 版 exe（观感更好），其次 tkinter 版，最后退回 .cmd。"""
    for 名 in ("核工坊Qt.exe", "核工坊.exe"):
        exe = os.path.join(根目录, "dist", 名)
        if os.path.exists(exe):
            return '"%s" "%%1"' % exe, exe
    cmd = os.path.join(根目录, "核工坊.cmd")
    return '"%s" "%%1"' % cmd, cmd


打开命令, _所用程序 = _打开程序()


def _运行(命令):
    结果 = subprocess.run(命令, capture_output=True, text=True, shell=False)
    return 结果.returncode, (结果.stdout or "") + (结果.stderr or "")


def 注册():
    if not os.path.exists(图标):
        print("找不到图标：%s" % 图标)
        return 1
    命令集 = [
        ["reg", "add", r"HKCU\Software\Classes\%s" % 类名, "/ve", "/d", 描述, "/f"],
        ["reg", "add", r"HKCU\Software\Classes\%s\DefaultIcon" % 类名, "/ve", "/d", 图标, "/f"],
        [
            "reg",
            "add",
            r"HKCU\Software\Classes\%s\shell\open\command" % 类名,
            "/ve",
            "/d",
            打开命令,
            "/f",
        ],
        ["reg", "add", r"HKCU\Software\Classes\%s" % 扩展名, "/ve", "/d", 类名, "/f"],
        ["reg", "add", r"HKCU\Software\Classes\%s" % 扩展名, "/v", "Content Type", "/d", "text/plain", "/f"],
        ["reg", "add", r"HKCU\Software\Classes\%s" % 扩展名, "/v", "PerceivedType", "/d", "text", "/f"],
    ]
    失败 = 0
    for 命令 in 命令集:
        码, 输出 = _运行(命令)
        if 码 != 0:
            失败 += 1
            print("失败：%s\n%s" % (" ".join(命令), 输出.strip()))
    if 失败:
        return 1
    print("已关联 %s → %s" % (扩展名, 描述))
    print("双击 .xht 文件会用这个程序打开：%s" % _所用程序)
    print("图标取自 素材/核图标.ico。")
    print("如果资源管理器没刷新，注销再登录，或执行：ie4uinit.exe -show")
    _运行(["ie4uinit.exe", "-show"])
    return 0


def 查看():
    for 键 in (扩展名, 类名, r"%s\DefaultIcon" % 类名, r"%s\shell\open\command" % 类名):
        码, 输出 = _运行(["reg", "query", r"HKCU\Software\Classes\%s" % 键, "/ve"])
        print("== %s" % 键)
        print(输出.strip() or "（未设置）")
        print()
    return 0


def 取消():
    for 键 in (r"%s" % 类名, r"%s" % 扩展名):
        码, 输出 = _运行(["reg", "delete", r"HKCU\Software\Classes\%s" % 键, "/f"])
        print("删除 %s：%s" % (键, "好" if 码 == 0 else 输出.strip()))
    return 0


if __name__ == "__main__":
    参数 = sys.argv[1:]
    if "--查看" in 参数:
        sys.exit(查看())
    if "--取消" in 参数:
        sys.exit(取消())
    sys.exit(注册())
