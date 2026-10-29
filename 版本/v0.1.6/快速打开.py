# -*- coding: utf-8 -*-
"""快速打开文件对话框（类似 PyCharm 的 Search Everywhere）。

在项目目录里按文件名模糊匹配，回车打开。
"""

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout,
)

跳过目录 = {"__pycache__", "build", "dist", "版本", ".git", ".idea", ".vscode"}
跳过后缀 = (".pyc", ".pkg", ".pyz", ".toc", ".exe", ".zip")


class 快速打开(QDialog):
    def __init__(self, 主窗):
        super().__init__(主窗)
        self.主窗 = 主窗
        self.setWindowTitle("快速打开")
        self.setModal(True)
        self.resize(560, 420)
        self.setStyleSheet(主窗.styleSheet())
        # 主窗换主题时由 核工坊Qt.主窗._同步对话框样式 重新套一遍
        self.跟主题 = True

        self.全部文件 = self._收集(主窗.项目目录)
        self.候选 = list(self.全部文件)

        布局 = QVBoxLayout(self)
        布局.setContentsMargins(14, 12, 14, 12)
        布局.setSpacing(8)

        self.输入框 = QLineEdit()
        self.输入框.setObjectName("输入框")
        self.输入框.setPlaceholderText("输入文件名过滤，回车打开，Esc 关闭")
        self.输入框.textChanged.connect(self._过滤)
        self.输入框.returnPressed.connect(self._打开选中)
        布局.addWidget(self.输入框)

        self.列表 = QListWidget()
        self.列表.itemActivated.connect(lambda _: self._打开选中())
        布局.addWidget(self.列表, 1)

        self.提示 = QLineEdit()
        self.提示.setReadOnly(True)
        self.提示.setObjectName("crumb")
        self.提示.setText("共 %d 个文件" % len(self.全部文件))
        布局.addWidget(self.提示)

        self._过滤("")
        self.输入框.setFocus()

    def _收集(self, 根):
        结果 = []
        for 目录, 子目录, 文件 in os.walk(根):
            子目录[:] = [d for d in 子目录 if d not in 跳过目录 and not d.startswith(".")]
            for 名 in 文件:
                if 名.startswith(".") or 名.endswith(跳过后缀):
                    continue
                if not 名.endswith((".xht", ".py", ".md", ".txt", ".json")):
                    continue
                全 = os.path.join(目录, 名)
                结果.append((os.path.relpath(全, 根), 全))
        return sorted(结果, key=lambda x: x[0].lower())

    def _过滤(self, 词):
        词 = 词.strip().lower()
        self.列表.clear()
        if not 词:
            self.候选 = self.全部文件[:200]
        else:
            # 简单模糊：按字符出现顺序匹配，文件名命中优先
            命中 = []
            for 相对, 全 in self.全部文件:
                名 = os.path.basename(相对).lower()
                if 词 in 名:
                    命中.append((0, 相对, 全))
                elif 词 in 相对.lower():
                    命中.append((1, 相对, 全))
            命中.sort()
            self.候选 = [(r, p) for _, r, p in 命中[:200]]
        for 相对, _全 in self.候选:
            QListWidgetItem(相对, self.列表)
        if self.列表.count():
            self.列表.setCurrentRow(0)
        self.提示.setText(
            "共 %d 个文件，匹配 %d 个" % (len(self.全部文件), len(self.候选))
        )

    def _打开选中(self):
        项 = self.列表.currentItem()
        if 项 is None:
            return
        相对 = 项.text()
        for 相对路径, 全 in self.候选:
            if 相对路径 == 相对:
                self.主窗.打开(全)
                # close() 让 exec() 正常返回，再交给事件循环回收。
                # 直接 destroy() 在模态循环里可能卡住。
                self.close()
                self.deleteLater()
                return
