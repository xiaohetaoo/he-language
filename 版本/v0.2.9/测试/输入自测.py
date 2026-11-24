# -*- coding: utf-8 -*-
"""编辑器输入自测：专测「吞字」。

用户报过「每行会吞字」。QTest.keyClicks 遇到非 ASCII 会直接断言失败
（qasciikey.cpp:192），所以中文必须走 QInputMethodEvent 模拟输入法上屏，
不能用 keyClicks 假装打字——之前的复现失败就是栽在这里。

用法：python 测试/输入自测.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.argv = [sys.argv[0]]

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QInputMethodEvent, QKeyEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

import 核工坊Qt as gq

失败 = []


def 检查(条件, 说明):
    if 条件:
        print("  ok   %s" % 说明)
    else:
        print("  FAIL %s" % 说明)
        失败.append(说明)


def 主():
    应用 = QApplication(sys.argv)
    应用.setApplicationName("核工坊")

    窗 = gq.主窗()
    窗.resize(1200, 760)
    窗.show()

    def 冲(次=40):
        for _ in range(次):
            应用.processEvents()

    冲()
    编 = 窗.当前
    编.setFocus()
    冲()

    def 上屏(文本, 预编辑=""):
        """模拟输入法：可先给预编辑（组字中），再提交上屏。"""
        if 预编辑:
            编.inputMethodEvent(QInputMethodEvent(预编辑, []))
        事件 = QInputMethodEvent()
        事件.setCommitString(文本)
        编.inputMethodEvent(事件)

    print("[ASCII 连打不丢字]")
    编.置文本("")
    冲()
    # 不含引号：引号有自动配对，会额外插入另一半，不属于丢字
    样本 = "abc(){}[]<>=+-*/0123456789," * 4
    QTest.keyClicks(编, 样本)
    冲(60)
    检查(编.toPlainText() == 样本, "连续键入 %d 个字符，一个不少" % len(样本))

    print("[引号自动配对]")
    编.置文本("")
    冲()
    QTest.keyClicks(编, "ab")
    QTest.keyClick(编, Qt.Key_Apostrophe)
    QTest.keyClick(编, Qt.Key_QuoteDbl)
    冲(30)
    # 自动配对后光标停在中间，所以第二个引号会插进第一个的肚子里
    检查(编.toPlainText() == "ab'\"\"'", "单双引号各自动补齐：%r" % 编.toPlainText())

    print("[输入法逐字上屏]")
    编.置文本("")
    冲()
    期 = "这是一个很长的中文句子用来测试输入法逐字上屏有没有吞字"
    for 字 in 期:
        上屏(字, 预编辑="nihao")
    冲(60)
    检查(编.toPlainText() == 期, "逐字上屏 %d 字全部到位" % len(期))

    print("[输入法整串上屏]")
    编.置文本("")
    冲()
    上屏(期)
    冲(30)
    检查(编.toPlainText() == 期, "一次性上屏整串不丢")

    print("[输入法连打两百字]")
    编.置文本("")
    冲()
    长 = "核语言是一门用中文写的编程语言用来检验大量输入的性能" * 10
    上屏(长)
    冲(60)
    检查(编.toPlainText() == 长, "一次上屏 %d 字不丢" % len(长))

    print("[输入法中文标点]")
    编.置文本("")
    冲()
    上屏("你好")
    上屏("“")
    上屏("世界")
    上屏("”")
    上屏("，")
    冲(30)
    检查(编.toPlainText() == "你好“世界”，", "中文引号逗号不被自动配对吃掉")

    print("[组字中不抢按键]")
    编.置文本("")
    冲()
    # 输入法候选窗开着时按引号，自动配对必须让路，否则输入法收不到按键，
    # 正在组的那段就被吞掉。这里用 preedit 标记组字状态。
    编.inputMethodEvent(QInputMethodEvent("ni", []))
    冲(5)
    检查(编._组字中 is True, "组字中状态被正确记录")
    编._组字中 = True
    编.keyPressEvent(QKeyEvent(QEvent.KeyPress, 0, Qt.NoModifier, "'"))
    冲(5)
    检查(编.toPlainText() == "", "组字中按引号不会自动补一对，留给输入法")
    编._组字中 = False
    # 提交组字内容
    事件 = QInputMethodEvent()
    事件.setCommitString("你")
    编.inputMethodEvent(事件)
    冲(5)
    检查(编.toPlainText() == "你", "组字提交后正常上屏")
    检查(编._组字中 is False, "提交后组字状态清除")

    print("[连续组字四十五次不丢]")
    编.置文本("")
    冲()
    期连 = "输入法连续组字测试这是一句比较长的话用来验证稳定性"
    for 字 in 期连:
        编.inputMethodEvent(QInputMethodEvent("pinyin", []))
        事件 = QInputMethodEvent()
        事件.setCommitString(字)
        编.inputMethodEvent(事件)
    冲(40)
    检查(编.toPlainText() == 期连, "连续组字 %d 次全部上屏" % len(期连))

    print("[中间插入]")
    编.置文本("末尾")
    冲()
    游 = 编.textCursor()
    游.setPosition(0)
    编.setTextCursor(游)
    冲()
    上屏("开头")
    冲(30)
    检查(编.toPlainText() == "开头末尾", "光标移到开头插入，位置正确")

    print("[回车自动缩进]")
    编.置文本("    缩进行")
    冲()
    游 = 编.textCursor()
    游.movePosition(游.MoveOperation.End)
    编.setTextCursor(游)
    冲()
    QTest.keyClick(编, Qt.Key_Return)
    上屏("下一行")
    冲(30)
    检查(编.toPlainText() == "    缩进行\n    下一行", "回车沿用上一行缩进：%r" % 编.toPlainText())

    print("[撤销不丢结构]")
    编.置文本("一二三四五")
    冲()
    游 = 编.textCursor()
    游.movePosition(游.MoveOperation.End)
    编.setTextCursor(游)
    上屏("六七八")
    冲(30)
    编.undo()
    冲(30)
    检查("一二三四五" in 编.toPlainText(), "撤销后原内容还在：%r" % 编.toPlainText())

    print("[大文件输入不错位]")
    编.置文本("\n".join("第 %d 行内容" % i for i in range(500)))
    冲(60)
    游 = 编.textCursor()
    游.setPosition(0)
    编.setTextCursor(游)
    冲()
    上屏("插到最前")
    冲(60)
    检查(编.toPlainText().startswith("插到最前"), "五百行文件里在开头插入，位置正确")

    编.已改 = False
    窗.close()
    冲(10)

    print()
    if 失败:
        print("输入自测失败 %d 项：" % len(失败))
        for 项 in 失败:
            print("  - %s" % 项)
        return 1
    print("输入自测全部通过（吞字、输入法、缩进、插入位置）")
    return 0


if __name__ == "__main__":
    sys.exit(主())
