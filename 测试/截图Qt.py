# -*- coding: utf-8 -*-
"""生成 README / 说明.md 用的界面截图（Qt 版）。

截图一律用 窗口.grab()：屏幕抓图会被其他窗口遮挡，
PrintWindow 又会丢 DWM 标题栏，只有进程内渲染最可靠。

用法：python 测试/截图Qt.py
"""
import os
import sys

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 根)
sys.argv = [sys.argv[0]]

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import 核工坊Qt
import 设置窗口Qt


def 等(应用, 次=12):
    for _ in range(次):
        应用.processEvents()


def 主():
    应用 = QApplication.instance() or QApplication(sys.argv)
    窗 = 核工坊Qt.主窗()
    窗.resize(1500, 940)
    窗.show()
    等(应用, 20)

    # 直接用例子文件，截图里就是用户真能看到的代码
    窗.换主题("深色")
    窗.打开(os.path.join(根, "例子", "03_容器与函数.xht"))
    等(应用, 20)
    窗.grab().toImage().save(os.path.join(根, "截图_核工坊.png"))
    print("深色 ok", flush=True)

    # 行号对齐特写（用户报过「行标是歪的」，这里留一张能看清的证据图）
    if 窗.当前 is not None:
        窗.当前.grab().toImage().copy(0, 0, 560, 210).save(
            os.path.join(根, "截图_行号对齐.png")
        )
        print("行号特写 ok", flush=True)

    # 设置窗口
    框 = 设置窗口Qt.设置对话框(窗)
    框.resize(760, 580)
    框.show()
    等(应用, 15)
    框.grab().toImage().save(os.path.join(根, "截图_设置.png"))
    print("设置 ok", flush=True)
    框.close()
    等(应用, 5)

    # 浅色
    窗.换主题("浅色")
    等(应用, 20)
    窗.grab().toImage().save(os.path.join(根, "截图_核工坊_浅色.png"))
    print("浅色 ok", flush=True)

    # 欢迎页：关掉全部文档
    窗.换主题("深色")
    for 编 in list(窗.文档集):
        编.已改 = False
        窗.关闭文档(编, 强制=True)
    等(应用, 15)
    窗.grab().toImage().save(os.path.join(根, "截图_欢迎页.png"))
    print("欢迎页 ok", flush=True)

    窗.close()
    return 0


if __name__ == "__main__":
    sys.exit(主())
