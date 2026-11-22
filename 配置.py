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


#: 上一次 读配置() 清洗掉的坏字段：[(字段名, 原因), …]。
#: 界面启动后读一次，把「有设置被重置成默认」这件事告诉用户 ——
#: 静默回退默认会让人以为设置莫名其妙丢了，却查不出原因。
上次问题 = []


def _可转整数(值):
    """能不能安全地当整数用（bool 不算 —— True 会变成 1，容易被误当制表宽）。"""
    if isinstance(值, bool):
        return None
    if isinstance(值, int):
        return 值
    if isinstance(值, float):
        # 有限性也要看：inf / nan 转 int 会抛 OverflowError / ValueError
        if 值 != 值 or 值 in (float("inf"), float("-inf")):
            return None
        return int(值)
    if isinstance(值, str):
        try:
            return int(值.strip())
        except (TypeError, ValueError):
            return None
    return None


def _清洗配置(原):
    """按 schema 校验配置，返回 (干净配置, 问题列表)。

    为什么必须有这一层（P1-7）：`读配置()` 以前只挡住了「JSON 解析失败」，
    一经成功就原样返回。而配置文件是可以被手改、被别的版本写、被同步工具
    截断的。实测这几种「合法 JSON、错误类型」全都会让程序**启动即崩**：

        []            → AttributeError: 'list' object has no attribute 'get'
        "文本"        → 同上
        123 / null    → 同上
        制表宽="abc"  → ValueError: invalid literal for int()
        项目目录=123  → TypeError: expected str, bytes or os.PathLike … not int
        窗口尺寸=123  → TypeError: argument of type 'int' is not iterable

    处理原则：**坏字段丢掉（由调用方的默认值兜底），好字段一个不动**。
    丢掉而不是「修成一个猜的值」—— 猜错了用户更难查。
    """
    问题 = []
    if not isinstance(原, dict):
        问题.append(("(整个文件)", "顶层不是对象（实际是 %s）" % type(原).__name__))
        return {}, 问题

    净 = {}
    for 键, 值 in 原.items():
        坏 = None

        if 键 == "制表宽":
            数 = _可转整数(值)
            if 数 is None or not (1 <= 数 <= 16):
                坏 = "不是 1–16 的整数"
            else:
                值 = 数

        elif 键 == "字号":
            数 = _可转整数(值)
            if 数 is None:
                坏 = "不是整数"
            else:
                值 = 数

        elif 键 in ("缩进线", "行号", "自动高亮"):
            if not isinstance(值, bool):
                坏 = "不是 true/false"

        elif 键 == "最近":
            if not isinstance(值, list):
                坏 = "不是列表"
            else:
                值 = [x for x in 值 if isinstance(x, str)]
                if len(值) != len(原[键]):
                    坏 = "列表里有非字符串项（已丢弃那些项）"
                    # 这一条不算「整个字段作废」：合法项留着更有用
                    问题.append((键, 坏))
                    净[键] = 值
                    continue

        elif 键 in ("窗口尺寸", "窗口位置", "主题"):
            if not isinstance(值, str):
                坏 = "不是字符串"

        elif 键 == "项目目录":
            if not isinstance(值, str) or not 值.strip():
                坏 = "不是非空字符串"

        if 坏:
            问题.append((键, 坏))
            continue
        净[键] = 值
    return 净, 问题


def 读配置():
    """读配置。坏 JSON 或坏类型都回退默认，并通过 `上次问题` 留痕。"""
    global 上次问题
    上次问题 = []
    try:
        with open(配置路径(), encoding="utf-8") as f:
            原 = json.load(f)
    except Exception:
        上次问题 = [("(整个文件)", "读不出来或不是合法 JSON")]
        return {}
    净, 问题 = _清洗配置(原)
    上次问题 = 问题
    return 净


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
