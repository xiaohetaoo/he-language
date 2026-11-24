# -*- coding: utf-8 -*-
"""查找 / 替换的实际行为。

盯的是几件容易悄悄坏掉的事：
1. 替换词里含查找词（甲 → 甲乙）不能原地打转；
2. 全部替换要算**一次**撤销，光标要回到原处；
3. 区分大小写的口径，查找和替换必须一致；
4. 找不到时光标不许跳到文首；
5. 「替换」按钮的提示不能被随后的定位改写掉。

用法：python 测试/查替换.py
"""

import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("核工坊_配置目录", tempfile.mkdtemp(prefix="核工坊替换_"))

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication  # noqa: E402
from PySide6.QtGui import QTextCursor  # noqa: E402

import 核工坊Qt  # noqa: E402
import 查找对话框  # noqa: E402

应用 = QApplication.instance() or QApplication(sys.argv)
窗 = 核工坊Qt.主窗()

问题 = []


def 检(条件, 说明):
    if 条件:
        print("  ok   %s" % 说明)
    else:
        问题.append(说明)
        print("  !!   %s" % 说明)


def 取编():
    return 窗.当前 or 窗.新建()


def 摆(编, 文, 位=None):
    编.置文本(文)
    游 = 编.textCursor()
    游.setPosition(len(文) if 位 is None else 位)
    编.setTextCursor(游)


print("== 一、替换词里含查找词 ==")
编 = 取编()
摆(编, "甲 甲 甲\n")
次 = 编.全部替换("甲", "甲乙")
检(次 == 3 and 编.取文本() == "甲乙 甲乙 甲乙\n", "甲→甲乙 只替换原来的 3 处，不无限套娃")

print("== 二、替换成空串 ==")
摆(编, "甲乙甲乙甲\n")
次 = 编.全部替换("甲", "")
检(次 == 3 and 编.取文本() == "乙乙\n", "批量删词")

print("== 三、区分大小写 ==")
摆(编, "Abc abc ABC\n")
次 = 编.全部替换("abc", "x", True)
检(次 == 1 and 编.取文本() == "Abc x ABC\n", "区分大小写只换全小写那一处")
摆(编, "Abc abc ABC\n")
次 = 编.全部替换("abc", "x", False)
检(次 == 3 and 编.取文本() == "x x x\n", "不区分大小写三处全换")

print("== 四、全部替换算一次撤销 ==")
摆(编, "甲 甲 甲\n")
编.全部替换("甲", "乙")
编.undo()
检(编.取文本() == "甲 甲 甲\n", "Ctrl+Z 一次全部还原")

print("== 五、全部替换后光标回到原处 ==")
# 回归：以前存的是 QTextCursor 对象，它跟着文档一起被推走，
# 读回来的已经是新位置（实测 4 → 5），「放回原处」等于没放。
摆(编, "甲 甲 甲\n", 4)
编.全部替换("甲", "乙")
检(编.textCursor().position() == 4,
   "光标仍在第 4 个字符处（实际 %d）" % 编.textCursor().position())

print("== 六、查找绕回与失败时的光标 ==")
摆(编, "甲 乙 甲\n")
检(编.查找下一个("甲") and 编.textCursor().selectedText() == "甲",
   "光标在末尾也能绕回文首找到")
摆(编, "甲 乙 丙\n", 5)
检(not 编.查找下一个("不存在") and 编.textCursor().position() == 5,
   "找不到时光标留在原处，不跳文首")

print("== 七、替换当前不误换别的词 ==")
摆(编, "甲 乙 丙\n")
游 = 编.textCursor()
游.setPosition(2)
游.setPosition(3, QTextCursor.KeepAnchor)   # 选中的是「乙」
编.setTextCursor(游)
成 = 编.替换当前("甲", "X")
检(成 and 编.取文本() == "X 乙 丙\n", "选中的不是查找词时，另找一处再换")

print("== 八、替换按钮的提示不被定位改写 ==")
摆(编, "甲 甲\n")
框 = 查找对话框.查找对话框(窗, 编)
框.查找框.setText("甲")
框.替换框.setText("乙")
框.替换当前()
检("已替换 1 处" in 框.计数.text(),
   "提示里说得出「已替换 1 处」（实际 %r）" % 框.计数.text())
框.替换当前()
检("没有更多了" in 框.计数.text(),
   "最后一处替换完要说「没有更多了」（实际 %r）" % 框.计数.text())
框.close()
框.deleteLater()

print()
print("=" * 62)
if 问题:
    print("发现 %d 处查找替换异常：" % len(问题))
    for 说明 in 问题:
        print("  · %s" % 说明)
    sys.exit(1)
print("查找替换行为正常")