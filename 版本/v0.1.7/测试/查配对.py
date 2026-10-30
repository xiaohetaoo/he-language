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
    """模拟逐字符输入（无修饰，只适合不需要 Shift 的字符）。"""
    for ch in 串:
        事件 = QKeyEvent(QEvent.KeyPress, 0, Qt.NoModifier, ch)
        编.keyPressEvent(事件)


# 真实 Windows（US/中文）键盘上每个符号的按键形态：
# (  )  {  }  "  都必须按住 Shift 才打得出来，Qt 给出的
# key 是键位码、modifiers 带 ShiftModifier、text 才是真正要输入的字符。
# 这就是 0.0.8 那个回归的盲区：测试一直用 NoModifier + 字符当 key 的
# 假事件，天然绕过了 `not 事件.modifiers()` 这道检查。
真键 = {
    "(": (Qt.Key_ParenLeft, Qt.ShiftModifier),
    ")": (Qt.Key_ParenRight, Qt.ShiftModifier),
    "[": (Qt.Key_BracketLeft, Qt.NoModifier),
    "]": (Qt.Key_BracketRight, Qt.NoModifier),
    "{": (Qt.Key_BraceLeft, Qt.ShiftModifier),
    "}": (Qt.Key_BraceRight, Qt.ShiftModifier),
    '"': (Qt.Key_QuoteDbl, Qt.ShiftModifier),
    "'": (Qt.Key_Apostrophe, Qt.NoModifier),
}


def 打真(编, 串):
    """按真实键盘形态逐字符输入。"""
    for ch in 串:
        键, 修 = 真键.get(ch, (0, Qt.NoModifier))
        编.keyPressEvent(QKeyEvent(QEvent.KeyPress, 键, 修, ch))


def 放(编, 初始):
    编.置文本(初始)
    编.setFocus()
    游 = 编.textCursor()
    游.movePosition(QTextCursor.End)
    编.setTextCursor(游)


def 试(初始, 输入, 期望, 说明):
    编 = 窗.当前 or 窗.新建()
    放(编, 初始)
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


def 试真(初始, 输入, 期望, 说明):
    """真实键盘形态的输入。"""
    编 = 窗.当前 or 窗.新建()
    放(编, 初始)
    打真(编, 输入)
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

print("== 真实键盘形态（Shift 键位）==")
# 0.0.8 回归：这四个符号在真实键盘上必然带 ShiftModifier，
# 而检查写的是 `not 事件.modifiers()`，于是全都只输入单个字符、不配对。
for 名, 串 in (
    ("圆括号", "(x)"),
    ("方括号", "[x]"),
    ("花括号", "{x}"),
    ("双引号", '"中"'),
    ("单引号", "'中'"),
):
    试真("", 串, 串, "真实键盘打%s" % 名)

# 只按第一个键 —— 配对是否真的发生，看有没有自动补上另一半
for ch, 剩 in (("(", ")"), ("[", "]"), ("{", "}"), ('"', '"'), ("'", "'")):
    编 = 窗.当前 or 窗.新建()
    放(编, "")
    打真(编, ch)
    实际 = 编.取文本()
    if 实际 != ch + 剩:
        问题.append(("真实键盘单个 %r 要自动配对" % ch, "", ch, ch + 剩, 实际))
        print("  !! 真实键盘按 %r -> %r（应为 %r）" % (ch, 实际, ch + 剩))
    else:
        print("  OK  真实键盘按 %r -> %r" % (ch, 实际))

print("== Ctrl/Alt 组合要让路给快捷键 ==")
for ch, 修, 名 in (
    ("(", Qt.ControlModifier, "Ctrl+("),
    ("{", Qt.ControlModifier | Qt.ShiftModifier, "Ctrl+Shift+{"),
    ('"', Qt.AltModifier, "Alt+\""),
):
    编 = 窗.当前 or 窗.新建()
    放(编, "")
    键 = 真键[ch][0]
    编.keyPressEvent(QKeyEvent(QEvent.KeyPress, 键, 修, ch))
    实际 = 编.取文本()
    if len(实际) > 1:
        问题.append(("%s 不该自动配对" % 名, "", ch, ch, 实际))
        print("  !! %s 不该配对，实际 %r" % (名, 实际))
    else:
        print("  OK  %s 没有自动配对（%r）" % (名, 实际))

print()
print("=" * 62)
if 问题:
    print("发现 %d 处配对行为异常：" % len(问题))
    for 说明, 初始, 输入, 期望, 实际 in 问题:
        print("  · %s" % 说明)
    sys.exit(1)
print("自动配对行为正常")
