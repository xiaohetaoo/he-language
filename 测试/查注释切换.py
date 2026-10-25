# -*- coding: utf-8 -*-
"""切换注释的行为验证。

要点：
  · 「核核 」和英文「#」都要认；
  · 取消注释后内容要原样恢复（不吞字、不多空格）；
  · 混排文件里每行按自己的风格处理；
  · 空行不动；
  · 「核核紧贴」不是注释（判定与 核.py 翻译器一致）。

用法：python 测试/查注释切换.py
"""

import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("核工坊_配置目录", tempfile.mkdtemp(prefix="核工坊注释_"))

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication  # noqa: E402
from PySide6.QtGui import QTextCursor  # noqa: E402

import 核工坊Qt  # noqa: E402

应用 = QApplication.instance() or QApplication(sys.argv)
窗 = 核工坊Qt.主窗()

问题 = []


def 切(文本, 次数=1):
    """在文本上切换注释 次数 次，返回结果。"""
    编 = 窗.当前 or 窗.新建()
    编.置文本(文本)
    游 = 编.textCursor()
    游.movePosition(QTextCursor.Start)
    游.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
    编.setTextCursor(游)
    for _ in range(次数):
        编.切换注释()
    return 编.取文本()


def 检(说明, 输入, 次数, 期望):
    实际 = 切(输入, 次数)
    if 实际 != 期望:
        问题.append((说明, 输入, 期望, 实际))
        print("  !! %s" % 说明)
        print("       输入=%r（切 %d 次）" % (输入, 次数))
        print("       期望=%r" % 期望)
        print("       实际=%r" % 实际)
    else:
        print("  OK  %s -> %r" % (说明, 实际))


print("== 加注释（切 1 次）==")
检("中文代码加注释", "注释\n", 1, "核核 注释\n")
检("英文代码加注释", "hello\n", 1, "核核 hello\n")
检("缩进代码加注释", "    x = 1\n", 1, "    核核 x = 1\n")
检("多行加注释", "a = 1\nb = 2\n", 1, "核核 a = 1\n核核 b = 2\n")
检("含空行加注释", "a = 1\n\nb = 2\n", 1, "核核 a = 1\n\n核核 b = 2\n")
检("核核紧贴不算注释", "核核紧贴\n", 1, "核核 核核紧贴\n")

print("== 取消注释（切 1 次）==")
检("取消中文注释", "核核 注释\n", 1, "注释\n")
检("取消英文注释", "# hello\n", 1, "hello\n")
检("取消无空格英文注释", "#hello\n", 1, "hello\n")
检("取消缩进注释", "    核核 注释\n", 1, "    注释\n")
检("取消多行注释", "核核 a = 1\n核核 b = 2\n", 1, "a = 1\nb = 2\n")
检("取消混排注释", "核核 a\n# b\n核核 c\n", 1, "a\nb\nc\n")

print("== 来回切换（切 2 次）==")
检("中文来回", "注释\n", 2, "注释\n")
检("英文来回", "hello\n", 2, "hello\n")
检("已是注释来回", "核核 注释\n", 2, "核核 注释\n")
检("多行来回", "a = 1\nb = 2\n", 2, "a = 1\nb = 2\n")

print("== 英文注释的风格 ==")
# 取消英文注释再重新加上，会改用核语言的「核核 」——
# 因为取消之后那一行已经看不出原来用的是哪个符号了。
# 这是可以接受的：核语言自己的写法就该是「核核 」。
检("英文注释改用核核", "# hello\n", 2, "核核 hello\n")

print()
print("=" * 62)
if 问题:
    print("发现 %d 处问题：" % len(问题))
    for 说明, 输入, 期望, 实际 in 问题:
        print("  · %s" % 说明)
    sys.exit(1)
print("切换注释行为正常")
