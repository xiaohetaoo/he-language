# -*- coding: utf-8 -*-
"""量一下「有折叠时每敲一键重算折叠可见性」的实际代价。

0.0.13 给折叠区加了缓存（见 编辑器.折叠区 / 折叠数据），这个脚本就是用来看
到底省了多少的。基准数字（本机、offscreen、阶梯式嵌套）：

    行数     缓存前     缓存后
     500     1.2ms      0.4ms
    2000     4.6ms      2.4ms
    8000    18.7ms      7.1ms

剩下那部分是「必须遍历每一块确认可见性」的固定开销，省不掉。

用法：python 测试/量折叠.py
"""

import os
import sys
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("核工坊_配置目录", tempfile.mkdtemp(prefix="量折叠_"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtGui import QTextCursor  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import 核工坊Qt  # noqa: E402

应用 = QApplication.instance() or QApplication(sys.argv)
窗 = 核工坊Qt.主窗()


def 造(行数, 嵌套):
    """嵌套：缩进 0/4/8/12 循环，折叠区域层层套住，最吃缓存。"""
    行集 = []
    for i in range(行数):
        if i % 10 == 0:
            行集.append(" " * ((i // 10) % 4 * 4 if 嵌套 else 0) + "核若 核对：")
        else:
            行集.append(" " * (16 if 嵌套 else 4) + "核说(%d)" % i)
    return "\n".join(行集)


for 嵌套 in (True, False):
    print("== %s ==" % ("嵌套折叠" if 嵌套 else "并列折叠"))
    for 行数 in (500, 2000, 8000):
        编 = 窗.当前 or 窗.新建()
        编.置文本(造(行数, 嵌套))
        编.全部折叠()
        游 = 编.textCursor()
        游.movePosition(QTextCursor.End)
        编.setTextCursor(游)
        n = 40
        起 = time.perf_counter()
        for _ in range(n):
            编.应用折叠()
        耗 = (time.perf_counter() - 起) / n * 1000
        print("  %6d 行：%6.2f ms/次（折叠块 %d）" % (行数, 耗, 编._折叠数))

print()
print("== 缓存命中情况 ==")
编 = 窗.当前 or 窗.新建()
编.置文本(造(2000, False))
编._编辑位置 = -1
起 = time.perf_counter()
编.全部折叠()
print("  首次（建缓存）：%.2f ms" % ((time.perf_counter() - 起) * 1000))
起 = time.perf_counter()
for _ in range(20):
    编.应用折叠()
print("  后续（吃缓存）：%.2f ms/次" % ((time.perf_counter() - 起) / 20 * 1000))
# 改一行：只有覆盖它的那个折叠范围该失效
块 = 编.document().findBlockByNumber(1005)
游 = QTextCursor(块)
游.movePosition(QTextCursor.EndOfBlock)
编.setTextCursor(游)
编.insertPlainText("x")
编._编辑位置 = 游.position()
起 = time.perf_counter()
编.应用折叠()
print("  改一行之后：%.2f ms" % ((time.perf_counter() - 起) * 1000))
