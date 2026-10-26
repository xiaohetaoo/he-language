# -*- coding: utf-8 -*-
"""版本控制面板（Qt 版，**只读**）。

只展示「当前分支 / 有哪些文件改过 / 与上游差几个提交」，
双击一行把那个文件在编辑器里打开。

**刻意不做提交、暂存、推送** —— 原因写在 版本控制.py 的模块注释里：
推送有硬约定，界面上的按钮会变成绕过约定的快捷路径。
这里给一句提示，让想提交的人知道该去哪儿做。
"""

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout,
)

import 版本控制


class 版本控制窗口(QDialog):
    def __init__(self, 主窗, 目录):
        super().__init__(主窗)
        self.主窗 = 主窗
        self.目录 = 目录
        self.setWindowTitle("版本控制")
        self.setModal(False)
        self.resize(620, 460)
        self.setStyleSheet(主窗.styleSheet())
        self._建界面()
        self.刷新()

    def _建界面(self):
        布局 = QVBoxLayout(self)
        布局.setContentsMargins(18, 16, 18, 14)
        布局.setSpacing(8)

        标 = QLabel("版本控制")
        标.setObjectName("pageTitle")
        布局.addWidget(标)

        self.概要 = QLabel("")
        self.概要.setObjectName("hintText")
        布局.addWidget(self.概要)

        self.树 = QTreeWidget()
        self.树.setColumnCount(2)
        self.树.setHeaderLabels(["状态", "文件"])
        self.树.setRootIsDecorated(False)
        self.树.setAlternatingRowColors(False)
        self.树.setColumnWidth(0, 90)
        self.树.itemDoubleClicked.connect(self._双击)
        布局.addWidget(self.树, 1)

        self.空提示 = QLabel("")
        self.空提示.setObjectName("hintText")
        self.空提示.setWordWrap(True)
        布局.addWidget(self.空提示)

        行 = QHBoxLayout()
        行.addStretch(1)
        for 文本, 槽, 主钮 in (
            ("刷新", self.刷新, False),
            ("打开所在目录", self._打开目录, False),
            ("关闭", self.close, True),
        ):
            钮 = QPushButton(文本)
            # 不设 autoDefault：否则 Qt 会把默认按钮转给其中一个，
            # 回车键就去执行它，而不是用户以为的动作。
            钮.setAutoDefault(False)
            if 主钮:
                钮.setProperty("primary", "true")
            钮.clicked.connect(槽)
            行.addWidget(钮)
        布局.addLayout(行)

    # —— 刷新 ——

    def 刷新(self):
        self.树.clear()
        状态 = 版本控制.状态(self.目录)
        self.状态 = 状态

        if not 状态["可用"]:
            原因 = 状态.get("原因") or "不可用"
            self.概要.setText("未启用：%s" % 原因)
            self.空提示.setText(
                "版本控制面板需要 git。\n"
                "没装 git、或者当前项目目录不在 git 仓库里时，这里会一直是空的。\n"
                "代码编辑、运行、保存都不受这个面板影响。"
            )
            return

        分支 = 状态["分支"]
        改 = 状态["改动"]
        尾 = []
        if 状态["有上游"]:
            if 状态["领先"]:
                尾.append("领先上游 %d 个提交" % 状态["领先"])
            if 状态["落后"]:
                尾.append("落后上游 %d 个提交" % 状态["落后"])
            if not 尾:
                尾.append("与上游一致")
        else:
            尾.append("没有配置上游")
        self.概要.setText(
            "分支 %s　·　%d 个文件有改动　·　%s" % (分支, len(改), "，".join(尾))
        )

        for 码位, 路径 in 改:
            说明, _色 = 版本控制.说明状态(码位)
            项 = QTreeWidgetItem([说明, 路径])
            项.setData(0, Qt.UserRole, 路径)
            项.setToolTip(1, os.path.join(self.目录, 路径))
            self.树.addTopLevelItem(项)

        if 改:
            self.空提示.setText(
                "双击一行可以在编辑器里打开该文件。"
                "本面板只做展示 —— 提交与推送请在命令行或 git 客户端里进行"
                "（推送前需要确认）。"
            )
        else:
            self.空提示.setText("工作区干净，没有未提交的改动。")

    # —— 操作 ——

    def _双击(self, 项, _列):
        相对 = 项.data(0, Qt.UserRole)
        if not 相对:
            return
        全 = os.path.join(self.目录, 相对)
        if not os.path.isfile(全):
            self.主窗.状态("文件不在了：%s" % 相对)
            return
        self.主窗.打开(全)

    def _打开目录(self):
        if not os.path.isdir(self.目录):
            self.主窗.状态("目录不存在")
            return
        try:
            os.startfile(self.目录)
        except Exception as e:  # noqa: BLE001
            self.主窗.状态("打不开目录：%s" % e)
