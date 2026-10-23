# -*- coding: utf-8 -*-
"""用真实桌面截屏验证最大化后四角有没有露出桌面/阴影。"""
import ctypes
import ctypes.wintypes as wt
import os
import sys
import tempfile

os.environ["核工坊_配置目录"] = tempfile.mkdtemp()
这里 = r"D:\dsh\dsh5"
sys.path.insert(0, 这里)
sys.argv = ["x"]

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

import 核工坊Qt

应用 = QApplication.instance() or QApplication(sys.argv)
窗 = 核工坊Qt.主窗()
窗.show()
for _ in range(15):
    应用.processEvents()


def 拍(名):
    屏 = QGuiApplication.primaryScreen()
    图 = 屏.grabWindow(0).toImage()
    w, h = 图.width(), 图.height()
    # 窗口最大化的可见范围：0..可用区（像素）
    dpr = 屏.devicePixelRatio()
    可 = 屏.availableGeometry()
    右 = int(可.right() * dpr)
    下 = int(可.bottom() * dpr)
    点们 = {
        "屏幕左上": (0, 0),
        "屏幕左上内": (2, 2),
        "窗口右上": (右 - 1, 0),
        "窗口左下": (0, 下 - 1),
        "窗口右下": (右 - 1, 下 - 1),
    }
    print("== %s == 可用区像素 0..%d x 0..%d, dpr=%.1f" % (名, 右, 下, dpr))
    for k, (x, y) in 点们.items():
        c = 图.pixelColor(int(x), int(y))
        print("   %-10s %s" % (k, c.name()))
    图.save(os.path.join(这里, "测试", "_桌面_%s.png" % 名))


拍("还原态")

窗.showMaximized()
for _ in range(40):
    应用.processEvents()
拍("最大化")

for d in list(窗.文档集):
    d.已改 = False
窗.close()
应用.processEvents()
