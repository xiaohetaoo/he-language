# -*- coding: utf-8 -*-
"""核工坊 Qt 版设置对话框（外观 / 编辑器 / 运行 / 关于 四页）。"""

import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

import 主题

这里 = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, 这里)

import 核  # noqa: E402


class 设置对话框(QDialog):
    """四个分类页的设置窗口。改动立即预览，取消则还原。"""

    分类 = ["外观", "编辑器", "运行", "关于"]

    def __init__(self, 主窗):
        super().__init__(主窗)
        self.主窗 = 主窗
        self.结果 = False
        # 记住打开时的状态，供「取消」还原
        self.原始 = {
            "主题名": 主窗.主题名,
            "字号": 主窗.字号,
            "制表宽": 主窗.制表宽,
            "缩进线": 主窗.显示缩进线,
            "行号": 主窗.显示行号,
        }

        self.setWindowTitle("设置")
        self.setModal(True)
        self.resize(720, 560)
        # 独立窗口不会自动继承父窗口样式，必须显式套一份
        self.setStyleSheet(主题.生成样式(主窗.主题, 主窗.字号))
        if os.path.exists(os.path.join(这里, "素材", "核图标.ico")):
            from PySide6.QtGui import QIcon

            self.setWindowIcon(QIcon(os.path.join(这里, "素材", "核图标.ico")))

        self._建界面()

    def _建界面(self):
        外层 = QHBoxLayout(self)
        外层.setContentsMargins(0, 0, 0, 0)
        外层.setSpacing(0)

        # 左侧分类
        self.左栏 = QListWidget()
        self.左栏.setFixedWidth(160)
        self.左栏.setObjectName("sidePanel")
        for 名 in self.分类:
            QListWidgetItem(名, self.左栏)
        self.左栏.currentRowChanged.connect(self._切页)
        外层.addWidget(self.左栏)

        # 右侧内容 + 底部按钮
        右 = QWidget()
        右布局 = QVBoxLayout(右)
        右布局.setContentsMargins(24, 20, 24, 16)
        右布局.setSpacing(12)

        self.标题 = QLabel("外观")
        self.标题.setStyleSheet(
            "font-size: 17px; font-weight: bold; color: %s;" % self.主窗.主题["文本"]
        )
        右布局.addWidget(self.标题)

        self.说明 = QLabel("")
        self.说明.setStyleSheet("color: %s;" % self.主窗.主题["次要文本"])
        右布局.addWidget(self.说明)

        self.栈 = QStackedWidget()
        self.栈.addWidget(self._页外观())
        self.栈.addWidget(self._页编辑器())
        self.栈.addWidget(self._页运行())
        self.栈.addWidget(self._页关于())
        右布局.addWidget(self.栈, 1)

        按钮行 = QWidget()
        按钮布局 = QHBoxLayout(按钮行)
        按钮布局.setContentsMargins(0, 0, 0, 0)
        按钮布局.addStretch(1)
        for 文本, 槽, 主要 in (
            ("确定", self.确定, True),
            ("应用", self.应用, False),
            ("取消", self.取消, False),
        ):
            钮 = QPushButton(文本)
            if 主要:
                钮.setDefault(True)
            钮.clicked.connect(槽)
            按钮布局.addWidget(钮)
        右布局.addWidget(按钮行)

        外层.addWidget(右, 1)
        self.左栏.setCurrentRow(0)
        self._切页(0)

    def _分组(self, 文本):
        标 = QLabel(文本)
        标.setStyleSheet(
            "font-weight: bold; color: %s; margin-top: 6px;" % self.主窗.主题["文本"]
        )
        return 标

    def _页外观(self):
        页 = QWidget()
        布局 = QVBoxLayout(页)
        布局.setContentsMargins(0, 0, 0, 0)
        布局.setSpacing(10)

        布局.addWidget(self._分组("配色"))
        行 = QHBoxLayout()
        self.主题框 = QComboBox()
        for 名 in 主题.主题集:
            self.主题框.addItem(名)
        self.主题框.setCurrentText(self.主窗.主题名)
        self.主题框.currentTextChanged.connect(self._换主题)
        行.addWidget(self.主题框)
        行.addStretch(1)
        布局.addLayout(行)

        布局.addWidget(self._分组("字号"))
        行2 = QHBoxLayout()
        self.字号框 = QComboBox()
        # 必须把「改字号」实际能达到的每个值都列全（那边是 9~22 逐个加减），
        # 否则当前值不在列表里时 findData 返回 -1、下拉框显示成 9 pt，
        # 用户一按确定字号就被悄悄改回 9。
        可选 = list(range(9, 23))
        当前 = int(self.主窗.字号)
        if 当前 not in 可选:
            可选.append(当前)
            可选.sort()
        for n in 可选:
            self.字号框.addItem("%d pt" % n, n)
        位置 = self.字号框.findData(当前)
        self.字号框.setCurrentIndex(位置 if 位置 >= 0 else 0)
        self.字号框.currentIndexChanged.connect(self._换字号)
        行2.addWidget(self.字号框)
        行2.addStretch(1)
        布局.addLayout(行2)

        布局.addWidget(self._分组("界面元素"))
        self.勾行号 = QCheckBox("显示行号")
        self.勾行号.setChecked(self.主窗.显示行号)
        self.勾行号.stateChanged.connect(self._换行号)
        布局.addWidget(self.勾行号)

        self.勾缩进线 = QCheckBox("显示缩进参考线")
        self.勾缩进线.setChecked(self.主窗.显示缩进线)
        self.勾缩进线.stateChanged.connect(self._换缩进线)
        布局.addWidget(self.勾缩进线)

        布局.addStretch(1)
        return 页

    def _页编辑器(self):
        页 = QWidget()
        布局 = QVBoxLayout(页)
        布局.setContentsMargins(0, 0, 0, 0)
        布局.setSpacing(10)

        布局.addWidget(self._分组("缩进"))
        行 = QHBoxLayout()
        行.addWidget(QLabel("每级缩进空格数"))
        self.缩进框 = QComboBox()
        # 同上：当前值必须能在下拉框里找到，否则一按确定就被改成列表首项
        可缩 = [2, 4, 8]
        当前缩 = int(self.主窗.制表宽)
        if 当前缩 not in 可缩:
            可缩.append(当前缩)
            可缩.sort()
        for n in 可缩:
            self.缩进框.addItem("%d 空格" % n, n)
        位缩 = self.缩进框.findData(当前缩)
        self.缩进框.setCurrentIndex(位缩 if 位缩 >= 0 else 0)
        self.缩进框.currentIndexChanged.connect(self._换制表宽)
        行.addWidget(self.缩进框)
        行.addStretch(1)
        布局.addLayout(行)

        布局.addWidget(self._分组("行为"))
        self.勾高亮 = QCheckBox("输入时自动语法高亮")
        self.勾高亮.setChecked(getattr(self.主窗, "自动高亮", True))
        布局.addWidget(self.勾高亮)

        布局.addStretch(1)
        return 页

    def _页运行(self):
        页 = QWidget()
        布局 = QVBoxLayout(页)
        布局.setContentsMargins(0, 0, 0, 0)
        布局.setSpacing(10)

        布局.addWidget(self._分组("项目目录"))
        行 = QHBoxLayout()
        self.目录框 = QLineEdit(getattr(self.主窗, "项目目录", 这里))
        self.目录框.setReadOnly(True)
        行.addWidget(self.目录框, 1)
        改 = QPushButton("更改…")
        改.clicked.connect(self._选目录)
        行.addWidget(改)
        布局.addLayout(行)

        布局.addWidget(self._分组("解释器"))
        布局.addWidget(
            QLabel(
                "核语言 %s  ·  Python %s"
                % (核.版本, sys.version.split()[0])
            )
        )
        布局.addStretch(1)
        return 页

    def _页关于(self):
        页 = QWidget()
        布局 = QVBoxLayout(页)
        布局.setContentsMargins(0, 0, 0, 0)
        布局.setSpacing(8)

        标 = QLabel("核语言 %s（Qt 版）" % 核.版本)
        标.setStyleSheet("font-size: 15px; font-weight: bold;")
        布局.addWidget(标)
        布局.addWidget(
            QLabel("用中文写程序 · 源文件后缀 %s" % 核.扩展名)
        )

        布局.addSpacing(10)
        for 名, 值 in (
            ("关键字", len(核.关键词表)),
            ("内置函数", len(核.函数表)),
            ("方法", len(核.方法表)),
            ("关键字参数", len(核.参数表)),
            ("异常类型", len(核.异常表)),
        ):
            行 = QHBoxLayout()
            左 = QLabel(名)
            左.setFixedWidth(90)
            行.addWidget(左)
            行.addWidget(QLabel(str(值)))
            行.addStretch(1)
            布局.addLayout(行)

        布局.addSpacing(14)
        链 = QLabel("查看最新版本与下载 → github.com/xiaohetaoo/he-language/releases")
        链.setStyleSheet("color: %s;" % self.主窗.主题["强调"])
        链.setCursor(Qt.PointingHandCursor)
        链.mousePressEvent = lambda e: self._打开发布页()
        布局.addWidget(链)

        布局.addStretch(1)
        return 页

    # —— 立即预览 ——

    def _切页(self, 行号):
        if not (0 <= 行号 < len(self.分类)):
            return
        self.栈.setCurrentIndex(行号)
        名 = self.分类[行号]
        self.标题.setText(名)
        self.说明.setText(
            {
                "外观": "主题与界面元素。改动立即预览。",
                "编辑器": "缩进与编辑行为。",
                "运行": "项目位置与运行环境。",
                "关于": "",
            }.get(名, "")
        )

    def _换主题(self, 名):
        self.主窗.换主题(名)
        self.setStyleSheet(主题.生成样式(self.主窗.主题, self.主窗.字号))

    def _换字号(self, _索引):
        n = self.字号框.currentData()
        if n:
            差 = int(n) - self.主窗.字号
            if 差:
                self.主窗.改字号(差)

    def _换行号(self, _状态):
        self.主窗.显示行号 = self.勾行号.isChecked()

    def _换缩进线(self, _状态):
        self.主窗.显示缩进线 = self.勾缩进线.isChecked()
        for d in self.主窗.文档集:
            d.update()

    def _换制表宽(self, _索引):
        n = self.缩进框.currentData()
        if n:
            self.主窗.制表宽 = int(n)
            for d in self.主窗.文档集:
                d.制表宽 = int(n)
                d.设置字体()

    def _选目录(self):
        from PySide6.QtWidgets import QFileDialog

        目录 = QFileDialog.getExistingDirectory(self, "选择项目文件夹", self.主窗.项目目录)
        if 目录:
            self.目录框.setText(目录)
            self.主窗.装载项目树(目录)

    def _打开发布页(self):
        地址 = "https://github.com/xiaohetaoo/he-language/releases"
        try:
            os.startfile(地址)
        except Exception:
            self.主窗.状态("打不开浏览器：%s" % 地址)

    # —— 提交 ——

    def 应用(self):
        self.结果 = True
        self.主窗.状态("设置已应用")

    def 确定(self):
        self.应用()
        self.destroy()

    def 取消(self):
        """把预览过的改动还原。"""
        主窗 = self.主窗
        if 主窗.主题名 != self.原始["主题名"]:
            主窗.换主题(self.原始["主题名"])
        差 = self.原始["字号"] - 主窗.字号
        if 差:
            主窗.改字号(差)
        主窗.制表宽 = self.原始["制表宽"]
        主窗.显示缩进线 = self.原始["缩进线"]
        主窗.显示行号 = self.原始["行号"]
        主窗.状态("设置已取消")
        self.结果 = False
        self.destroy()
