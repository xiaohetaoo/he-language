# -*- coding: utf-8 -*-
"""核数学库 / 核随机库：转译、成员真实性、真实数值三轮验证。

用法：
    python 测试/查标准库.py

验证四件事：
  1. 模块名与成员名转译正确（核数学库 -> math，核正弦 -> sin）
  2. 成员名在 Python 侧**真实存在**（`math.cbrt` 要 3.11+，防版本坑）
  3. 真的能跑出正确数值 —— 光转译对不算数
  4. 与既有对照表没有重名冲突（库成员在裸名和 `.` 后都生效，
     撞上函数表/方法表会让其中一个静默失效）
"""

import io
import math
import os
import random
import sys

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
    代码, _译 = 核.编译源码(源码, "<查标准库>", 报告)
    if 代码 is None:
        return None
    缓冲 = io.StringIO()
    旧 = sys.stdout
    sys.stdout = 缓冲
    try:
        核.执行代码(代码, 源码, "<查标准库>", None, 流=缓冲)
    finally:
        sys.stdout = 旧
    return 缓冲.getvalue()


# ---------------------------------------------------------------- 一、转译
def 测转译():
    print("[转译]")

    译 = 核.转译("核导入 核数学库\n")
    检查("import math" in 译, "`核导入 核数学库` -> import math（实际：%r）" % 译.strip())

    译 = 核.转译("核导入 核随机库\n")
    检查("import random" in 译, "`核导入 核随机库` -> import random（实际：%r）" % 译.strip())

    译 = 核.转译("核从 核数学库 核导入 核正弦, 核余弦\n")
    检查(
        "from math import sin, cos" in 译,
        "`核从 核数学库 核导入 核正弦, 核余弦` -> from math import sin, cos（实际：%r）"
        % 译.strip(),
    )

    译 = 核.转译("核从 核随机库 核导入 核随机整数\n")
    检查(
        "from random import randint" in 译,
        "`核从 核随机库 核导入 核随机整数` -> from random import randint（实际：%r）"
        % 译.strip(),
    )

    译 = 核.转译("x = 核数学库.核正弦(1)\n")
    检查(
        "math.sin(1)" in 译,
        "`核数学库.核正弦(1)` -> math.sin(1)（实际：%r）" % 译.strip(),
    )

    译 = 核.转译("x = 核随机库.核随机整数(1, 6)\n")
    检查(
        "random.randint(1, 6)" in 译,
        "`核随机库.核随机整数(1, 6)` -> random.randint(1, 6)（实际：%r）" % 译.strip(),
    )

    # 全角括号也要能认（代码区 NFKC 归一）
    译 = 核.转译("x = 核数学库.核平方根（9）\n")
    检查(
        "math.sqrt(9)" in 译,
        "全角括号 `核平方根（9）` 也认（实际：%r）" % 译.strip(),
    )

    # 英文原名照旧可用
    译 = 核.转译("x = math.sin(1)\n")
    检查("math.sin(1)" in 译, "英文原名 `math.sin(1)` 原样保留")


# ------------------------------------------------------- 二、成员是否真实存在
def 测成员存在():
    print()
    print("[成员真实性]")
    缺 = []
    for 中, 英 in sorted(核.库成员表.items()):
        if not (hasattr(math, 英) or hasattr(random, 英)):
            缺.append("%s -> %s" % (中, 英))
    检查(
        not 缺,
        "库成员表里每个英文名都真实存在%s" % ("（不存在：%s）" % "、".join(缺) if 缺 else ""),
    )

    # 单独点出 cbrt：3.11 才有，低版本会 AttributeError
    检查(
        hasattr(math, "cbrt"),
        "math.cbrt 存在（Python %d.%d，该函数需要 3.11+）"
        % (sys.version_info[0], sys.version_info[1]),
    )

    检查(
        核.模块表.get("核数学库") == "math" and 核.模块表.get("核随机库") == "random",
        "模块表把两个库指向 math / random",
    )


# ---------------------------------------------------------------- 三、真实数值
def 测真实运行():
    print()
    print("[真实运行]")

    源码 = (
        "核导入 核数学库\n"
        "核说(核数学库.核圆周率)\n"
        "核说(核数学库.核正弦(核数学库.核圆周率 / 2))\n"
        "核说(核数学库.核平方根(16))\n"
        "核说(核数学库.核进一取整(3.2))\n"
        "核说(核数学库.核舍尾取整(3.8))\n"
        "核说(核数学库.核最大公约(12, 18))\n"
        "核说(核数学库.核阶乘(5))\n"
    )
    出 = 跑(源码)
    检查(出 is not None, "数学库脚本编译通过")
    if 出 is None:
        return
    行 = 出.strip().splitlines()
    期望 = [
        repr(math.pi),
        repr(math.sin(math.pi / 2)),
        repr(math.sqrt(16)),
        repr(math.ceil(3.2)),
        repr(math.floor(3.8)),
        repr(math.gcd(12, 18)),
        repr(math.factorial(5)),
    ]
    检查(
        行 == 期望,
        "七个数与 Python 直接算的一致（实际：%s）" % 行,
    )

    # 随机库：先定种子，结果必须可复现
    源码 = (
        "核导入 核随机库\n"
        "核随机库.核随机种子(1234)\n"
        "甲 = []\n"
        "核用 i 遍历 核数列(6)：\n"
        "    甲.核加入(核随机库.核随机整数(1, 100))\n"
        "核说(甲)\n"
        "核随机库.核随机种子(1234)\n"
        "乙 = []\n"
        "核用 i 遍历 核数列(6)：\n"
        "    乙.核加入(核随机库.核随机整数(1, 100))\n"
        "核说(乙)\n"
    )
    出 = 跑(源码)
    检查(出 is not None, "随机库脚本编译通过")
    if 出 is None:
        return
    行 = 出.strip().splitlines()
    检查(len(行) == 2 and 行[0] == 行[1], "同一种子两次结果相同（%s）" % (行[:2],))

    # 与 Python 的 random 对拍：种子相同，序列必须一致
    random.seed(1234)
    对照 = [random.randint(1, 100) for _ in range(6)]
    检查(
        行 and 行[0] == repr(对照),
        "与 Python random 同种子序列一致（本机 %s，核语言 %s）"
        % (repr(对照), 行[0] if 行 else "无"),
    )

    # 从序列里取：结果必须来自给定集合
    源码 = (
        "核导入 核随机库\n"
        "核说(核随机库.核随机选一(['甲', '乙', '丙']))\n"
        "核说(核随机库.核随机采样(['甲', '乙', '丙'], 2))\n"
    )
    出 = 跑(源码)
    检查(出 is not None, "选一 / 采样脚本编译通过")
    if 出 is None:
        return
    行 = 出.strip().splitlines()
    检查(行 and 行[0] in ("甲", "乙", "丙"), "核随机选一 取到了集合内的元素（%s）" % (行[0] if 行 else "无"))


# ---------------------------------------------------------------- 四、无冲突
def 测无冲突():
    print()
    print("[重名冲突]")

    交 = set(核.库成员表) & set(核.方法表)
    检查(not 交, "库成员与方法不同名%s" % ("（撞到：%s）" % "、".join(sorted(交)) if 交 else ""))

    交 = set(核.库成员表) & set(核.函数表)
    检查(not 交, "库成员与函数不同名%s" % ("（撞到：%s）" % "、".join(sorted(交)) if 交 else ""))

    交 = set(核.模块表) & (set(核.函数表) | set(核.方法表) | set(核.关键词表))
    检查(not 交, "模块名不与函数/方法/关键字同名%s" % ("（撞到：%s）" % "、".join(sorted(交)) if 交 else ""))

    # 对照表.md 必须收录全部新名字（用户照着它写代码）
    表路径 = os.path.join(根目录, "对照表.md")
    if os.path.exists(表路径):
        with open(表路径, encoding="utf-8") as f:
            全文 = f.read()
        漏 = [k for k in list(核.模块表) + list(核.库成员表) if k not in 全文]
        检查(
            not 漏,
            "对照表.md 收录了模块表与库成员表的全部中文名%s"
            % ("（漏掉：%s）" % "、".join(漏[:8]) if 漏 else ""),
        )
    else:
        print("  ok   （对照表.md 尚未生成，跳过）")


def 主():
    print("核语言 标准库自检（版本 %s）" % 核.版本)
    print()
    测转译()
    测成员存在()
    测真实运行()
    测无冲突()
    print()
    if 失败:
        print("失败 %d 项：" % len(失败))
        for 项 in 失败:
            print("  - %s" % 项)
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(主())
