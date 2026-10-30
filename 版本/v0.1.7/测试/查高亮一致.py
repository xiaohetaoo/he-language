# -*- coding: utf-8 -*-
"""验证：语法高亮对「核核」的判断，与翻译器完全一致。

两处必须说同样的话 —— 否则同一行会被染成注释色、却又被当成代码。

做法：不复制任何判定逻辑，而是**真的跑一遍高亮器**，
看它把哪些字符段染成了注释色，再和转译结果对照。

用法：python 测试/查高亮一致.py
"""

import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("核工坊_配置目录", tempfile.mkdtemp(prefix="核工坊高亮_"))

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication  # noqa: E402

import 核  # noqa: E402
import 核工坊Qt  # noqa: E402

应用 = QApplication.instance() or QApplication(sys.argv)
窗 = 核工坊Qt.主窗()

样本 = [
    "核核 abc",
    "核核紧贴",
    "核核",
    "核核abc",
    "x核核 abc",
    "核核  ",
    "核核\t缩进",
    "核核。",
    "核核（括号）",
    "核核,逗号",
    "x = 1 核核 尾注",
    "  核核 缩进的注释",
    "核核 核说(核整数)",
    "核核abc 核核 def",
    "a核核b核核c",
    "核核_下划线",
    "_核核 x",
    "核核1数字",
    "# 英文注释",
    "核说(1)  # 尾注",
    "核说('核核 在字符串里')",
]

问题 = []
print("%-26s %-8s %-8s %s" % ("样本", "翻译器", "高亮器", "一致"))
print("-" * 62)

for s in 样本:
    # —— 翻译器的判定：译文里 # 的位置，就是注释的起点 ——
    译 = 核.转译(s)
    井 = 译.find("#")
    译认 = 井 >= 0

    # —— 高亮器的判定：真的建一个高亮器，看它有没有染出注释色 ——
    编 = 窗.当前 or 窗.新建()
    编.置文本(s)
    高 = 编.高亮
    高.重建()
    高.rehighlight()
    文档 = 编.document()
    块 = 文档.firstBlock()
    格式集 = set()
    for 段 in 块.layout().formats():
        格式集.add(段.format.foreground().color().name())
    from PySide6.QtGui import QColor  # noqa: E402

    目标 = QColor(窗.主题["注释"]).name()
    高认 = 目标 in 格式集

    一致 = 译认 == 高认
    if not 一致:
        问题.append((s, 译认, 高认))
    print("%-26r %-8s %-8s %s" % (s, 译认, 高认, "OK" if 一致 else "!! 不一致"))

print()
print("=" * 62)
if 问题:
    print("发现 %d 处不一致：" % len(问题))
    for s, a, b in 问题:
        print("  %r: 翻译器=%s 高亮器=%s" % (s, a, b))
    sys.exit(1)
print("高亮器与翻译器对「核核」的判断完全一致（%d 个样本）" % len(样本))
