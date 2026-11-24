# -*- coding: utf-8 -*-
"""Tab / Shift+Tab 缩进的实际按键行为。

这一份盯三件以前错过的事：
1. Shift+Tab 只认「正好一个制表宽的空格」或「正好一个制表符」，
   不足一级的缩进（粘来的 2 空格代码）、全角空格、空格+制表符混排
   一律退不掉，用户按了没反应。
2. 「Shift+↓ 选中一整行」得到的选区正好停在下一行行首，
   以前把那一行也算进缩进范围 —— 想缩一行，结果缩了两行。
3. 行中 Tab 要按**显示列**补到下一个制表位，全角字符占两列。

用法：python 测试/查缩进.py
"""

import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("核工坊_配置目录", tempfile.mkdtemp(prefix="核工坊缩进_"))

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication  # noqa: E402
from PySide6.QtGui import QKeyEvent, QTextCursor  # noqa: E402
from PySide6.QtCore import QEvent, Qt  # noqa: E402

import 核工坊Qt  # noqa: E402

应用 = QApplication.instance() or QApplication(sys.argv)
窗 = 核工坊Qt.主窗()

问题 = []


def 检(条件, 说明):
    if 条件:
        print("  ok   %s" % 说明)
    else:
        问题.append(说明)
        print("  !!   %s" % 说明)


def 按键(编, 键, 文=""):
    编.keyPressEvent(QKeyEvent(QEvent.KeyPress, 键, Qt.NoModifier, 文))


def 摆(编, 文, 起=None, 止=None):
    编.置文本(文)
    编.setFocus()
    游 = 编.textCursor()
    if 起 is None:
        游.movePosition(QTextCursor.End)
    else:
        游.setPosition(起)
        if 止 is not None:
            游.setPosition(止, QTextCursor.KeepAnchor)
    编.setTextCursor(游)


def 取编():
    return 窗.当前 or 窗.新建()


宽 = 取编().制表宽
print("制表宽 = %d" % 宽)

print("== 一、Shift+Tab 退得掉各种不足一级的缩进 ==")
for 缩进, 名 in (
    (" ", "一个空格"),
    ("  ", "两个空格"),
    ("   ", "三个空格"),
    ("\u3000", "全角空格"),
    (" \t", "空格加制表符"),
    ("\t", "一个制表符"),
):
    编 = 取编()
    原 = 缩进 + "甲 = 1\n"
    摆(编, 原, 0, len(原))
    按键(编, Qt.Key_Backtab)
    检(编.取文本() == "甲 = 1\n", "Shift+Tab 退掉%s" % 名)

print("== 二、一次只退一级，不能把八格缩进一口吞掉 ==")
编 = 取编()
原 = " " * (宽 * 2) + "甲 = 1\n"
摆(编, 原, 0, len(原))
按键(编, Qt.Key_Backtab)
检(编.取文本() == " " * 宽 + "甲 = 1\n", "八格缩进 Shift+Tab 只退到四格")

print("== 三、没缩进的行 Shift+Tab 不动它 ==")
编 = 取编()
摆(编, "甲 = 1\n", 0, 6)
按键(编, Qt.Key_Backtab)
检(编.取文本() == "甲 = 1\n", "顶格的行不被退成负缩进")

print("== 四、Tab 缩进再 Shift+Tab 回到原样 ==")
编 = 取编()
原 = "甲 = 1\n乙 = 2\n"
摆(编, 原, 0, len(原))
按键(编, Qt.Key_Tab)
中 = 编.取文本()
摆游 = 编.textCursor()
摆游.setPosition(0)
摆游.setPosition(len(中), QTextCursor.KeepAnchor)
编.setTextCursor(摆游)
按键(编, Qt.Key_Backtab)
检(编.取文本() == 原, "整块缩进再退回来，一个字不差")

print("== 五、选区停在下一行行首时不多缩那一行 ==")
编 = 取编()
文 = "甲 = 1\n乙 = 2\n丙 = 3\n"
# Shift+↓ 选中第一行：选区 0 → 6，6 正是第二行行首
摆(编, 文, 0, 6)
按键(编, Qt.Key_Tab)
检(编.取文本() == "    甲 = 1\n乙 = 2\n丙 = 3\n",
   "Shift+↓ 选一行再 Tab，只缩这一行")
# 选到第二行中间：两行都该缩
摆(编, 文, 0, 9)
按键(编, Qt.Key_Tab)
检(编.取文本() == "    甲 = 1\n    乙 = 2\n丙 = 3\n",
   "选区确实跨到第二行，两行都缩")
# 无选区、光标停在第二行行首：只缩第二行
摆(编, 文, 6)
按键(编, Qt.Key_Tab)
检(编.取文本() == "甲 = 1\n    乙 = 2\n丙 = 3\n",
   "无选区时光标在哪行缩哪行")

print("== 六、行中 Tab 按显示列补到下一个制表位 ==")
# 全角字符占两列：n 个「甲」= 2n 列，补到下一个 4 的倍数
for 个数 in (1, 2, 3, 4, 5):
    编 = 取编()
    摆(编, "甲" * 个数)
    按键(编, Qt.Key_Tab)
    列 = 个数 * 2
    应补 = 宽 - (列 % 宽)
    检(len(编.取文本()) == 个数 + 应补,
       "%d 个全角字符后 Tab 补 %d 个空格" % (个数, 应补))

print("== 七、整块缩进 / 退缩进各算一次撤销 ==")
编 = 取编()
原 = "甲 = 1\n乙 = 2\n丙 = 3\n"
摆(编, 原, 0, len(原))
按键(编, Qt.Key_Tab)
编.undo()
检(编.取文本() == 原, "三行一起缩进，Ctrl+Z 一次全退回")

print()
print("=" * 62)
if 问题:
    print("发现 %d 处缩进行为异常：" % len(问题))
    for 说明 in 问题:
        print("  · %s" % 说明)
    sys.exit(1)
print("缩进行为正常")