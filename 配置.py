# -*- coding: utf-8 -*-
"""核工坊 Qt 版的配置持久化。

打包成单文件后 sys._MEIPASS 是每次启动新建、退出即删的临时目录，
配置写进去下次就读不到。所以打包版存到用户配置目录。
"""

import json
import os
import sys

这里 = os.path.dirname(os.path.abspath(__file__))


def 配置目录():
    if getattr(sys, "frozen", False):
        基 = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(基, "核工坊")
    return 这里


def 配置路径():
    return os.path.join(配置目录(), "工坊配置.json")


def 读配置():
    try:
        with open(配置路径(), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def 存配置(配置):
    try:
        目录 = 配置目录()
        if not os.path.isdir(目录):
            os.makedirs(目录, exist_ok=True)
        with open(配置路径(), "w", encoding="utf-8") as f:
            json.dump(配置, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
