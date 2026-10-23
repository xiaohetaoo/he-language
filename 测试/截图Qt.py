# -*- coding: utf-8 -*-
"""生成 README / 说明.md 用的界面截图（Qt 版）。

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


def 主():
    应用 = QApplication.instance() or QApplication(sys.argv)
    窗 = 核工坊Qt.主窗()
    窗.resize(1400, 880)
    窗.show()

    def 一():
        窗.换主题("深色")
        窗.打开(os.path.join(根, "例子", "03_容器与函数.xht"))
        QTimer.singleShot(700, 二)

    def 二():
        窗.grab().toImage().save(os.path.join(根, "截图_核工坊.png"))
        print("深色 ok", flush=True)
        窗.换主题("浅色")
        QTimer.singleShot(700, 三)

    def 三():
        窗.grab().toImage().save(os.path.join(根, "截图_核工坊_浅色.png"))
        print("浅色 ok", flush=True)
        # 欢迎页：关掉全部文档
        for 文档 in list(窗.文档集):
            文档.已改 = False
            窗.关闭文档(文档, 强制=True)
        QTimer.singleShot(600, 四)

    def 四():
        窗.grab().toImage().save(os.path.join(根, "截图_欢迎页.png"))
        print("欢迎页 ok", flush=True)
        对 = 设置窗口Qt.设置对话框(窗)
        对.show()
        状态["对"] = 对  # 用容器保存引用，闭包里直接赋值不会传出去
        QTimer.singleShot(600, 五)

    def 五():
        设置窗 = 状态.get("对")
        if 设置窗 is not None:
            设置窗.grab().save(os.path.join(根, "截图_设置.png"))
            print("设置 ok", flush=True)
        应用.quit()

    状态 = {}
    QTimer.singleShot(400, 一)
    return 应用.exec()


if __name__ == "__main__":
    sys.exit(主())
