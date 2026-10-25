# -*- coding: utf-8 -*-
"""自动配对括号的实际按键行为。

怀疑点：自动配对不看「右边是不是已经有配对的另一半」，
于是打引号收尾时会多出一个 —— 核说("中文") 打出来变成 核说("中文"")。

用法：python 测试/查配对.py
"""

import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("核工坊_配置目录", tempfile.mkdtemp(prefix="核工坊配对_"))

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication  # noqa: E402
from PySide6.QtGui import QKeyEvent, QTextCursor  # noqa: E402
from PySide6.QtCore import QEvent, Qt  # noqa: E402

import 核工坊Qt  # noqa: E402

应用 = QApplication.instance() or QApplication(sys.argv)
窗 = 核工坊Qt.主窗()

问题 = []


def 打(编, 串):
    """模拟逐字符输入。"""
    for ch in 串:
        事件 = QKeyEvent(QEvent.KeyPress, 0, Qt.NoModifier, ch)
        编.keyPressEvent(事件)


def 试(初始, 输入, 期望, 说明):
    编 = 窗.当前 or 窗.新建()
    编.置文本(初始)
    编.setFocus()
    # 光标放到末尾
    游 = 编.textCursor()
    游.movePosition(QTextCursor.End)
    编.setTextCursor(游)
    打(编, 输入)
    实际 = 编.取文本()
    if 实际 != 期望:
        问题.append((说明, 初始, 输入, 期望, 实际))
        print("  !! %s" % 说明)
        print("       初始=%r 输入=%r" % (初始, 输入))
        print("       期望=%r" % 期望)
        print("       实际=%r" % 实际)
    else:
        print("  OK  %s -> %r" % (说明, 实际))


print("== 引号收尾 ==")
试("", '核说("中文")', '核说("中文")', "打引号包裹中文")
试("", "核说('中文')", "核说('中文')", "打单引号包裹中文")

print("== 括号收尾 ==")
试("核说(", "1)", "核说(1)", "括号里打右括号收尾")
试("核说(", "1)", "核说(1)", "括号里打右括号收尾")

print("== 已有配对字符在右边 ==")
试("", "核说()", "核说()", "空括号")
试("", "核说(1)", "核说(1)", "括号里有内容")

print("== 字典/列表 ==")
试("", "核字典()", "核字典()", "字典字面量")

print("== 不该被配对的场景 ==")
试("x = 1", "# 注释", "x = 1# 注释", "# 注释")

print()
print("=" * 62)
if 问题:
    print("发现 %d 处配对行为异常：" % len(问题))
    for 说明, 初始, 输入, 期望, 实际 in 问题:
        print("  · %s" % 说明)
    sys.exit(1)
print("自动配对行为正常")
