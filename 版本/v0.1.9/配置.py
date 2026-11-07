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
    # 测试可以设 核工坊_配置目录 指到临时目录 —— 否则跑一轮测试就把
    # 用户真实的界面设置写坏了（曾经把制表宽写成 2，导致后续自测失败）。
    覆盖 = os.environ.get("核工坊_配置目录")
    if 覆盖:
        return 覆盖
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
    """写配置。**先写临时文件再原子替换**。

    以前直接 open(路径, "w")：写到一半崩溃、断电、或者杀进程，
    磁盘上就留下半截 JSON。而 读配置() 解析失败时是「静默返回 {}」，
    用户下次打开软件会发现主题、字号、行号、项目目录全被重置，
    而且完全没有提示 —— 半截文件比没有文件更糟。
    os.replace 在同一分区上是原子的：要么是旧内容，要么是新内容。
    """
    路径 = 配置路径()
    try:
        目录 = 配置目录()
        if not os.path.isdir(目录):
            os.makedirs(目录, exist_ok=True)
        临时 = 路径 + ".tmp"
        with open(临时, "w", encoding="utf-8", newline="\n") as f:
            json.dump(配置, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(临时, 路径)
    except Exception:
        # 写不进去也不能让界面崩掉；顺手清掉可能残留的临时文件
        try:
            if os.path.exists(路径 + ".tmp"):
                os.remove(路径 + ".tmp")
        except OSError:
            pass
