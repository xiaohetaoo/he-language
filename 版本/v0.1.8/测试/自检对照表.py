# -*- coding: utf-8 -*-
"""对照表自检：检查定义有无冲突、是否有中文名被两个英文共用。

用法：
    python 测试/自检对照表.py

检查项：
  1. 同一张表里，中文名不能重复（不然不知道译成哪个）
  2. 同一个英文不能被两个中文名映射（不然行为取决于书写顺序）
  3. 中文名不能与 Python 关键字/内置冲突（例如把 int 译成 print 的名字）
  4. 已定义的英文，是否都在「英文清单」里（漏了就认不出来）
"""

import os
import sys
from collections import Counter, defaultdict

这里 = os.path.dirname(os.path.abspath(__file__))
根目录 = os.path.dirname(这里)
sys.path.insert(0, 根目录)

import 核  # noqa: E402

失败 = []

#: 允许同一个英文对应多个中文名的情况：
#: `in` 既用于 `核用 i 遍历 x`（句式），也用于 `核在`（独立判断），
#: 两者上下文不同，属于有意复用，不算冲突。
允许重复英文 = {
    "in": {"遍历", "核在"},
}


def 检查(条件, 说明):
    if 条件:
        print("  ok   %s" % 说明)
    else:
        print("  FAIL %s" % 说明)
        失败.append(说明)


def 查重与冲突(表名, 映射, 英文清单=None):
    print("[%s]" % 表名)
    中文名 = list(映射.keys())
    英文名 = list(映射.values())

    重复中文 = [k for k, n in Counter(中文名).items() if n > 1]
    检查(not 重复中文, "中文名不重复%s" % ("（重复：%s）" % "、".join(重复中文) if 重复中文 else ""))

    重复英文 = []
    for 英, n in Counter(英文名).items():
        if n <= 1:
            continue
        用过 = {k for k, v in 映射.items() if v == 英}
        if 英 in 允许重复英文 and 用过 <= 允许重复英文[英]:
            continue
        重复英文.append(英)
    检查(not 重复英文, "英文名不重复%s" % ("（重复：%s）" % "、".join(重复英文) if 重复英文 else ""))

    # 中文名撞 Python 关键字会很危险：转译后成了 Python 自己的词
    if 表名 in ("关键词表", "参数表"):
        撞 = [k for k in 中文名 if k in 核.英文关键词]
        检查(not 撞, "中文名不撞 Python 关键字%s" % ("（撞到：%s）" % "、".join(撞) if 撞 else ""))
    else:
        撞 = [k for k in 中文名 if k in 核.英文内置]
        检查(not 撞, "中文名不撞 Python 内置%s" % ("（撞到：%s）" % "、".join(撞) if 撞 else ""))

    # 英文值必须在对应清单里，否则「中英都认」识别不到
    if 英文清单 is not None:
        漏 = [v for v in 英文名 if v not in 英文清单]
        检查(not 漏, "英文都在清单里%s" % ("（漏掉：%s）" % "、".join(漏) if 漏 else ""))


def 查覆盖(表名, 映射, 候选):
    """统计这类里有多少英文还没中文名。"""
    有 = set(映射.values()) & set(候选)
    无 = set(候选) - set(映射.values())
    print("[%s 覆盖]" % 表名)
    print("       已定义 %d / %d，待定义 %d" % (len(有), len(候选), len(无)))
    return len(无)


def 主():
    print("核语言 对照表自检（版本 %s）" % 核.版本)
    print()

    查重与冲突("关键词表", 核.关键词表, 核.英文关键词)
    查重与冲突("函数表", 核.函数表, 核.英文内置)
    查重与冲突("方法表", 核.方法表, 核.英文方法)
    查重与冲突("参数表", 核.参数表, 核.英文参数)

    print()
    print("[跨表冲突]")
    # 关键字与函数同名会让「这个中文词到底是语句还是函数」变得含糊
    交 = set(核.关键词表) & set(核.函数表)
    检查(not 交, "关键字与函数不同名%s" % ("（撞到：%s）" % "、".join(交) if 交 else ""))
    交2 = set(核.函数表) & set(核.方法表)
    # 函数与方法同名是允许的（上下文不同：一个裸用，一个在点后），仅提示
    if 交2:
        print("       提示：这些名字同时出现在函数表与方法表（允许，按上下文区分）：%s" % "、".join(sorted(交2)))

    print()
    print("[与文档一致性]")
    表路径 = os.path.join(根目录, "对照表.md")
    if os.path.exists(表路径):
        with open(表路径, encoding="utf-8") as f:
            全文 = f.read()
        for 表名, 映射 in (
            ("关键词表", 核.关键词表),
            ("函数表", 核.函数表),
            ("方法表", 核.方法表),
            ("参数表", 核.参数表),
        ):
            漏 = [k for k in 映射 if k not in 全文]
            检查(not 漏, "对照表.md 收录了 %s 的全部中文名%s" % (
                表名, "（漏掉：%s）" % "、".join(漏[:5]) if 漏 else ""))
        print("       提示：改了 核.py 的对照表后，重新运行 python 测试/生成对照表.py")
    else:
        print("       （还没生成 对照表.md）")

    print()
    if 失败:
        print("失败 %d 项：" % len(失败))
        for 项 in 失败:
            print("  - %s" % 项)
        return 1
    print("对照表自检全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(主())
