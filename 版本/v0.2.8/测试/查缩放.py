# -*- coding: utf-8 -*-
"""验证边缘判定与缩放光标（不真正调用 startSystemResize ——
那个会接管鼠标进入系统模态循环，测试里会卡住）。"""
import os
import sys

这里 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 这里)

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication

import 核工坊Qt

应用 = QApplication.instance() or QApplication(sys.argv)
窗 = 核工坊Qt.主窗()
窗.resize(1100, 760)
窗.show()
for _ in range(12):
    应用.processEvents()

宽, 高 = 窗.width(), 窗.height()
print("窗口: %dx%d  位置 %s" % (宽, 高, (窗.x(), 窗.y())))

案例 = [
    ("左边缘", (0, 高 // 2), Qt.LeftEdge),
    ("右边缘", (宽 - 1, 高 // 2), Qt.RightEdge),
    ("上边缘", (宽 // 2, 0), Qt.TopEdge),
    ("下边缘", (宽 // 2, 高 - 1), Qt.BottomEdge),
    ("左上角", (1, 1), Qt.LeftEdge | Qt.TopEdge),
    ("右下角", (宽 - 2, 高 - 2), Qt.RightEdge | Qt.BottomEdge),
    ("中心", (宽 // 2, 高 // 2), None),
    ("离边 20px", (20, 高 // 2), None),
]

错 = []
for 名, (x, y), 期望 in 案例:
    边 = 窗._落在边缘(窗.mapToGlobal(QPoint(x, y)))
    光标 = 窗._边缘光标(边)
    对 = (边 == 期望) if 期望 is not None else (边 is None)
    print("  %-10s -> 边=%s 光标=%s %s"
          % (名, 边, 光标, "OK" if 对 else "FAIL(期望 %s)" % 期望))
    if not 对:
        错.append(名)

# 最大化时不该响应边缘
窗.showMaximized()
for _ in range(15):
    应用.processEvents()
边 = 窗._落在边缘(窗.mapToGlobal(QPoint(1, 1)))
print("  最大化左上角 -> 边=%s %s" % (边, "OK（应为 None）" if 边 is None else "FAIL"))
if 边 is not None:
    错.append("最大化仍可拖边")

窗.showNormal()
应用.processEvents()

# 光标各边
for 名, e, 望 in (("左", Qt.LeftEdge, Qt.SizeHorCursor),
                  ("上", Qt.TopEdge, Qt.SizeVerCursor),
                  ("左上", Qt.LeftEdge | Qt.TopEdge, Qt.SizeFDiagCursor),
                  ("右上", Qt.RightEdge | Qt.TopEdge, Qt.SizeBDiagCursor)):
    got = 核工坊Qt.主窗._边缘光标(e)
    print("  光标 %-4s = %s %s" % (名, got, "OK" if got == 望 else "FAIL(期望 %s)" % 望))
    if got != 望:
        错.append("光标" + 名)

for d in list(窗.文档集):
    d.已改 = False
窗.close()
应用.processEvents()
print("\n结果:", "全部通过" if not 错 else "失败 %s" % 错)
sys.exit(0 if not 错 else 1)
