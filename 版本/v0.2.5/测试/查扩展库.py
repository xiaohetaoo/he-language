# -*- coding: utf-8 -*-
"""新标准库的转译、成员真实性、真实运行三轮验证。

覆盖 0.2.3 新增的四个模块：
  核时间库（time）/ 核路径库（os.path）/ 核系统库（os）/ 核命令行库（sys）
  / 核JSON库（json）/ 核网络库（urllib.request）

验证五件事：
  1. 模块名与成员名转译正确（核当前秒 -> time，核拼接路径 -> join）
  2. 成员名在 Python 侧**真实存在**（防手滑写错名字）
  3. 真的能跑出正确结果 —— 光转译对不算数
  4. 中文名全是合法标识符（含空格/ASCII 标点就没法被扫描器切出来）
  5. 与既有对照表没有重名冲突

用法：
    python 测试/查扩展库.py
"""

import importlib
import io
import json
import os
import sys
import time

这里 = os.path.dirname(os.path.abspath(__file__))
根目录 = os.path.dirname(这里)
sys.path.insert(0, 根目录)

import 核  # noqa: E402

失败 = []


def 检查(条件, 说明):
    if 条件:
        print("  ok   %s" % 说明)
    else:
        print("  FAIL %s" % 说明)
        失败.append(说明)


def 跑(源码):
    """转译并执行一段核语言，返回它打印出来的文本；编译不过返回 None。"""
    报告 = 核.未定义报告(None)
    代码, _译 = 核.编译源码(源码, "<查扩展库>", 报告)
    if 代码 is None:
        return None
    缓冲 = io.StringIO()
    旧 = sys.stdout
    sys.stdout = 缓冲
    try:
        核.执行代码(代码, 源码, "<查扩展库>", None, 流=缓冲)
    finally:
        sys.stdout = 旧
    return 缓冲.getvalue()


def 译(源码):
    报告 = 核.未定义报告(None)
    _代码, 译 = 核.编译源码(源码, "<查扩展库>", 报告)
    return 译


# ---------------------------------------------------------------- 一、表结构
def 测表结构():
    print("[表结构]")

    # 中文名必须是合法标识符 —— 否则扫描器根本切不出来
    坏模块 = [k for k in 核.模块表 if " " in k or not k.isidentifier()]
    坏成员 = [k for k in 核.库成员表 if " " in k or not k.isidentifier()]
    检查(not 坏模块, "模块表中文名全是合法标识符（问题：%r）" % 坏模块)
    检查(not 坏成员, "库成员表中文名全是合法标识符（问题：%r）" % 坏成员)

    # 值不能带点 —— from X import a.b 是非法 Python
    带点 = [(k, v) for k, v in 核.库成员表.items() if "." in v]
    检查(not 带点, "库成员表的值都不带点（问题：%r）" % 带点)

    # 一个中文名只能映射到一个英文名，反过来也应尽量唯一
    检查(
        len(set(核.库成员表.values())) == len(核.库成员表),
        "库成员表值无重复（%d 项，%d 个唯一值）"
        % (len(核.库成员表), len(set(核.库成员表.values()))),
    )


# ---------------------------------------------------------------- 二、成员真实性
def 测成员真实():
    print("[成员真实性]")

    实例 = {}
    for 英 in sorted(set(核.模块表.values())):
        实例[英] = importlib.import_module(英)

    缺 = []
    for 中, 英 in 核.库成员表.items():
        if not any(hasattr(m, 英) for m in 实例.values()):
            缺.append((中, 英))
    检查(not 缺, "表里每个成员在标准库里都真实存在（缺失：%r）" % 缺)

    # 每个模块都要能真的 import
    for 英, 模 in 实例.items():
        检查(模 is not None, "import %s 成功" % 英)


# ---------------------------------------------------------------- 三、转译
def 测转译():
    print("[转译]")

    检查(
        "import time" in 译("核导入 核时间库\n"),
        "`核导入 核时间库` -> import time",
    )
    检查(
        "import json" in 译("核导入 核JSON库\n"),
        "`核导入 核JSON库` -> import json",
    )
    检查(
        "import os.path" in 译("核导入 核路径库\n"),
        "`核导入 核路径库` -> import os.path",
    )
    检查(
        "from os.path import join" in 译("核从 核路径库 核导入 核拼接路径\n"),
        "`核从 核路径库 核导入 核拼接路径` -> from os.path import join",
    )
    检查(
        "from json import dumps" in 译("核从 核JSON库 核导入 核序列化\n"),
        "`核从 核JSON库 核导入 核序列化` -> from json import dumps",
    )
    检查(
        "time.time()" in 译("核说(核时间库.核当前秒())\n"),
        "`核时间库.核当前秒()` -> time.time()",
    )
    检查(
        "os.path.join(" in 译("核说(核路径库.核拼接路径('a','b'))\n"),
        "`核路径库.核拼接路径(…)` -> os.path.join(…)",
    )
    # 节名冲突：核时间库 的成员 time 与模块名 time 不冲突
    _译 = 译("核导入 核时间库\n核说(核时间库.核当前秒())\n")
    检查("import time" in _译 and "time.time()" in _译, "模块名与成员名可以同名不打架")


# ---------------------------------------------------------------- 四、真实运行
def 测真实运行():
    print("[真实运行]")

    # 时间库
    值 = 跑("核导入 核时间库\n核说(核时间库.核当前秒())\n")
    检查(值 is not None and float(值.strip()) > 0, "核当前秒() 返回正数")

    起 = time.time()
    跑("核从 核时间库 核导入 核睡眠\n核睡眠(0.05)\n")
    检查(time.time() - 起 >= 0.04, "核睡眠(0.05) 真的睡了")

    值 = 跑(
        "核从 核时间库 核导入 核格式化时间, 核本地时间\n"
        "核说(核格式化时间('%Y', 核本地时间()))\n"
    )
    检查(值 is not None and len(值.strip()) == 4, "核格式化时间('%Y') 返回 4 位年份")

    # 路径库
    值 = 跑(
        "核从 核路径库 核导入 核拼接路径, 核文件名, 核扩展名\n"
        "核说(核文件名(核拼接路径('D:', 'a', 'b.txt')))\n"
    )
    检查(值 is not None and 值.strip() == "b.txt", "核文件名(核拼接路径(…)) == b.txt")

    值 = 跑(
        "核从 核路径库 核导入 核扩展名\n"
        "核说(核扩展名('a.txt')[1])\n"
    )
    检查(值 is not None and 值.strip() == ".txt", "核扩展名('a.txt')[1] == .txt")

    # 系统库
    值 = 跑(
        "核导入 核系统库\n核说(核系统库.核工作目录())\n"
    )
    检查(值 is not None and len(值.strip()) > 0, "核工作目录() 返回非空路径")

    值 = 跑(
        "核从 核路径库 核导入 核路径存在\n"
        "核说(核路径存在('.'))\n"
    )
    检查(值 is not None and 值.strip() == "True", "核路径存在('.') == True")

    # JSON 库
    值 = 跑(
        "核从 核JSON库 核导入 核序列化\n"
        "核说(核序列化({'a': 1}))\n"
    )
    检查(值 is not None and "a" in 值, "核序列化({'a':1}) 含 a")

    值 = 跑(
        "核从 核JSON库 核导入 核反序列化\n"
        "核说(核反序列化('{\"a\": 3}')['a'])\n"
    )
    检查(值 is not None and 值.strip() == "3", "核反序列化 取到的 a == 3")

    # 与 Python 原生逐字对比
    值 = 跑(
        "核从 核JSON库 核导入 核序列化\n"
        "核说(核序列化({'x': [1, 2]}))\n"
    )
    期望 = json.dumps({"x": [1, 2]})
    检查((值 or "").strip() == 期望, "核序列化 与 json.dumps 逐字一致（%r vs %r）" % (值, 期望))


# ---------------------------------------------------------------- 五、反查
def 测反查():
    print("[反查与线索]")

    检查(len(核.库成员反查) > 0, "库成员反查 非空（%d 项）" % len(核.库成员反查))
    检查(
        核.库成员反查.get("strftime") == ("核时间库", "核格式化时间"),
        "strftime 反查到 核时间库.核格式化时间（实际：%r）" % (核.库成员反查.get("strftime"),),
    )
    检查(
        核.模块名反查.get("json") == "核JSON库",
        "json 反查到 核JSON库（实际：%r）" % (核.模块名反查.get("json"),),
    )


# ---------------------------------------------------------------- 六、不冲突
def 测不冲突():
    print("[与既有对照表不冲突]")

    冲突 = []
    for 表名, 表 in (
        ("关键词表", 核.关键词表),
        ("函数表", 核.函数表),
        ("方法表", 核.方法表),
        ("异常表", 核.异常表),
        ("参数表", 核.参数表),
    ):
        for 名 in 核.库成员表:
            if 名 in 表:
                冲突.append((表名, 名))
    检查(not 冲突, "库成员不与既有表重名（冲突：%r）" % 冲突)

    冲突 = [名 for 名 in 核.模块表 if 名 in 核.函数表 or 名 in 核.方法表]
    检查(not 冲突, "模块名不与函数/方法重名（冲突：%r）" % 冲突)


def 主():
    print("=" * 56)
    print("扩展标准库检查")
    print("=" * 56)
    测表结构()
    测成员真实()
    测转译()
    测真实运行()
    测反查()
    测不冲突()
    print("-" * 56)
    if 失败:
        print("失败 %d 项：" % len(失败))
        for 项 in 失败:
            print("  · %s" % 项)
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(主())
