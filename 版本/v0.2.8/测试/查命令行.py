# -*- coding: utf-8 -*-
"""命令行入口：路径不对时要给中文提示，不能甩英文 traceback。

实测过的问题：
  · 核 检查 不存在.xht  /  核 转译 不存在.xht
      → FileNotFoundError 的英文 traceback（运行 有中文提示，检查/转译没有）
  · 核 运行 例子（给的是目录）
      → PermissionError 的英文 traceback（三个入口都没拦目录）
  · 核 工坊 打开的是 tkinter 旧版（冻结在 0.0.6），不是主推的 Qt 版

用法：python 测试/查命令行.py
"""

import os
import subprocess
import sys
import tempfile

这里 = os.path.dirname(os.path.abspath(__file__))
根目录 = os.path.dirname(这里)
内核脚本 = os.path.join(根目录, "核.py")

问题 = []


def 跑(*参数, 目录=None):
    结果 = subprocess.run(
        [sys.executable, 内核脚本, *参数],
        capture_output=True,
        cwd=目录 or 根目录,
        env=dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1"),
        timeout=120,
    )
    return (
        结果.returncode,
        (结果.stdout or b"").decode("utf-8", "replace"),
        (结果.stderr or b"").decode("utf-8", "replace"),
    )


def 检(说明, 条件, 详情=""):
    if 条件:
        print("  OK  %s" % 说明)
    else:
        问题.append(说明)
        print("  !! %s" % 说明)
        if 详情:
            print("        %s" % 详情)


def 不该有英文堆栈(文本):
    return (
        "Traceback (most recent call last)" not in 文本
        and "FileNotFoundError" not in 文本
        and "PermissionError" not in 文本
        and "IsADirectoryError" not in 文本
    )


临时 = tempfile.mkdtemp(prefix="核命令行_")
缺失 = os.path.join(临时, "不存在.xht")

print("== 一、路径不存在 ==")
for 命令 in ("检查", "转译", "运行"):
    码, 出, 错 = 跑(命令, 缺失)
    检(
        "核 %s 不存在的文件：返回 2 且无英文堆栈" % 命令,
        码 == 2 and 不该有英文堆栈(出 + 错),
        "码=%r 出=%r 错=%r" % (码, 出, 错),
    )
    检(
        "核 %s 给中文提示" % 命令,
        "找不到文件" in (出 + 错),
        "出=%r 错=%r" % (出, 错),
    )

print("== 二、给的是目录 ==")
目录 = os.path.join(根目录, "例子")
for 命令 in ("检查", "转译", "运行"):
    码, 出, 错 = 跑(命令, 目录)
    检(
        "核 %s 传目录：返回 2、无英文堆栈、提示是目录" % 命令,
        码 == 2 and 不该有英文堆栈(出 + 错) and "目录" in (出 + 错),
        "码=%r 出=%r 错=%r" % (码, 出, 错),
    )

# 直接当命令写的时候也不能甩 traceback
码, 出, 错 = 跑(目录)
检(
    "核 目录：返回 2 且提示是目录",
    码 == 2 and "目录" in (出 + 错) and 不该有英文堆栈(出 + 错),
    "码=%r 出=%r 错=%r" % (码, 出, 错),
)

print("== 三、正常路径不受影响 ==")
样例 = os.path.join(根目录, "例子", "01_你好.xht")
码, 出, 错 = 跑("检查", 样例)
检("核 检查 正常文件通过", 码 == 0 and "检查通过" in 出, "码=%r 出=%r 错=%r" % (码, 出, 错))
码, 出, 错 = 跑("转译", 样例)
检("核 转译 正常文件有输出", 码 == 0 and "print" in 出, "码=%r 出=%r" % (码, 出))
码, 出, 错 = 跑("运行", 样例)
检("核 运行 正常文件返回 0", 码 == 0, "码=%r 出=%r 错=%r" % (码, 出, 错))

# 转译写出到不存在的目录
码, 出, 错 = 跑("转译", 样例, "-o", os.path.join(临时, "没有这个目录", "a.py"))
检(
    "核 转译 -o 写不出去时给中文提示",
    码 == 2 and "写不出文件" in (出 + 错) and 不该有英文堆栈(出 + 错),
    "码=%r 出=%r 错=%r" % (码, 出, 错),
)

print("== 四、核 工坊 指向 Qt 版 ==")
# 不能真的打开界面（测试环境没有显示器），只查入口分支指向哪个模块。
源码 = open(内核脚本, encoding="utf-8").read()
检("工坊 分支 import 核工坊Qt", "import 核工坊Qt" in 源码)
检("保留了 tkinter 旧版后门 工坊旧", "工坊旧" in 源码)
# import 核工坊Qt 失败时要退到旧版并说清楚原因
检("退到旧版时会说明原因", "改用 tkinter 旧界面" in 源码)

码, 出, 错 = 跑("帮助")
检("帮助里写的是 Qt 版工坊", "核 工坊" in 出 and "Qt 版" in 出, "出=%r" % 出[:200])
检("帮助里列出了工坊旧", "工坊旧" in 出)

print()
print("=" * 62)
if 问题:
    print("发现 %d 处命令行问题：" % len(问题))
    for 项 in 问题:
        print("  · %s" % 项)
    sys.exit(1)
print("命令行入口全部正常（中文提示、不甩堆栈）")
