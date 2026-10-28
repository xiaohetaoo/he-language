# -*- coding: utf-8 -*-
"""帮助相关的对话框（Qt 版）：版本历史、关于。

为什么单独一个文件：查找对话框、快速打开也都是各自一份，
主窗只负责「什么时候弹」，不塞界面细节。

样式上不写死任何颜色 —— 一律走 objectName 交给主题 QSS，
否则换到浅色主题时会变成看不见的浅灰（设置窗口踩过这个坑）。
"""

import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout,
)

这里 = os.path.dirname(os.path.abspath(__file__))
版本根 = os.path.join(这里, "版本")


def 版本排序键(名):
    """把 v0.0.11 这类目录名排成有序 —— 按数字逐段比较，不是按字典序。

    字典序会把 v0.0.10 排到 v0.0.9 前面（'1' < '9'）。
    异常命名（非 v 开头、段里有非数字）一律退回字符串比较，不抛异常。
    """
    try:
        return (0, [int(x) for x in 名[1:].split(".")])
    except (ValueError, IndexError):
        return (1, 名)


def 找版本根(额外=None):
    """所有可能存在 版本/ 的目录，按优先级返回。

    为什么要找多个：打包成单文件 exe 后，源码文件都在临时解包目录
    (`sys._MEIPASS`) 里，而 `版本/` **没有**打进 exe（十二份源码快照
    会让体积翻好几倍，不值得）。所以要看：
      1. 程序自己所在目录（源码运行时就是这里）
      2. 打包解包目录（万一以后把 版本/ 打进去了）
      3. 调用方给的目录 —— 通常是主窗的「项目目录」
    这样从项目文件夹里跑 exe，版本历史照样看得到。
    """
    候选 = [版本根]
    打包目录 = getattr(sys, "_MEIPASS", "")
    if 打包目录:
        候选.append(os.path.join(打包目录, "版本"))
    if 额外:
        候选.append(os.path.join(额外, "版本"))
    出 = []
    for 路径 in 候选:
        if 路径 and 路径 not in 出:
            出.append(路径)
    return 出


def 已归档版本(额外=None):
    """返回 [(版本名, 归档时间, 文件数), …]，按版本号从旧到新。

    会合并多个 版本/ 目录里的内容（同名的以先找到的那份为准）。
    """
    收集 = {}
    for 根 in 找版本根(额外):
        if not os.path.isdir(根):
            continue
        try:
            名们 = [d for d in os.listdir(根) if d.startswith("v")]
        except OSError:
            continue
        for 名 in 名们:
            路径 = os.path.join(根, 名)
            if not os.path.isdir(路径) or 名 in 收集:
                continue
            时间 = ""
            信息 = os.path.join(路径, "版本信息.txt")
            if os.path.isfile(信息):
                try:
                    with open(信息, encoding="utf-8") as f:
                        for 行 in f:
                            if 行.startswith("归档时间："):
                                时间 = 行.strip().split("：", 1)[1]
                                break
                except OSError:
                    pass
            文件数 = sum(len(fs) for _, _, fs in os.walk(路径))
            收集[名] = (名, 时间, 文件数)
    return sorted(收集.values(), key=lambda x: 版本排序键(x[0]))


class 版本历史对话框(QDialog):
    """列出 版本/ 下已归档的所有版本。"""

    def __init__(self, 主窗, 当前版本, 额外目录=None):
        super().__init__(主窗)
        self.主窗 = 主窗
        self.当前版本 = 当前版本
        # 额外在哪个目录里找 版本/ —— 打包版要传主窗的项目目录，
        # 否则 exe 里看不到任何归档（版本/ 没打进 exe）
        self.额外目录 = 额外目录 or getattr(主窗, "项目目录", None)
        self.setWindowTitle("版本历史")
        self.setModal(False)
        self.resize(520, 440)
        # 独立窗口不继承父窗口样式表，必须显式套一份
        self.setStyleSheet(主窗.styleSheet())
        # 主窗换主题时由 核工坊Qt.主窗._同步对话框样式 重新套一遍
        self.跟主题 = True
        self._建界面()

    def _建界面(self):
        布局 = QVBoxLayout(self)
        布局.setContentsMargins(20, 18, 20, 16)
        布局.setSpacing(10)

        标 = QLabel("核语言 版本历史")
        标.setObjectName("pageTitle")
        布局.addWidget(标)

        版本们 = 已归档版本(self.额外目录)
        说明 = QLabel(
            "当前版本 v%s　·　已归档 %d 个版本" % (self.当前版本, len(版本们))
        )
        说明.setObjectName("hintText")
        布局.addWidget(说明)

        框 = QPlainTextEdit()
        框.setReadOnly(True)
        框.setLineWrapMode(QPlainTextEdit.NoWrap)
        框.setPlainText(self._拼文本(版本们))
        布局.addWidget(框, 1)

        提示 = QLabel("完整说明见 版本记录.md")
        提示.setObjectName("hintText")
        布局.addWidget(提示)

        行 = QHBoxLayout()
        行.addStretch(1)
        for 文本, 槽, 主钮 in (
            ("打开版本目录", self._打开目录, False),
            ("查看版本记录", self._打开记录, False),
            ("关闭", self.close, True),
        ):
            钮 = QPushButton(文本)
            # 不设 autoDefault：否则 Qt 会把「默认按钮」转给其中一个，
            # 回车键就去执行它，而不是用户以为的那个动作。
            钮.setAutoDefault(False)
            if 主钮:
                钮.setProperty("primary", "true")
            钮.clicked.connect(槽)
            行.addWidget(钮)
        布局.addLayout(行)

    def _拼文本(self, 版本们):
        if not 版本们:
            return (
                "没有找到已归档的版本。\n\n"
                "「版本历史」读的是项目里的 版本/ 目录。\n"
                "打包成单个 exe 分发时，十二份源码快照会让体积翻几倍，\n"
                "所以 版本/ 没有打进 exe —— 这时看不到归档是正常的。\n\n"
                "要看版本历史，请在源码目录里运行，或把当前项目目录\n"
                "设成含 版本/ 的那个文件夹。\n\n"
                "归档一个新版本：\n"
                "    把 核.py 里的 版本 改成新版本号\n"
                "    python 测试/归档版本.py"
            )
        行 = []
        for 名, 时间, 文件数 in 版本们:
            标记 = "　← 当前" if 名 == "v%s" % self.当前版本 else ""
            行.append("%s%s" % (名, 标记))
            if 时间:
                行.append("      归档于 %s，%d 个文件" % (时间, 文件数))
            else:
                行.append("      %d 个文件" % 文件数)
        return "\n".join(行)

    def _打开目录(self):
        实际 = None
        for 根 in 找版本根(self.额外目录):
            if os.path.isdir(根):
                实际 = 根
                break
        if 实际 is None:
            self.主窗.状态("还没有 版本 目录")
            return
        try:
            os.startfile(实际)
        except Exception as e:  # noqa: BLE001
            self.主窗.状态("打不开目录：%s" % e)

    def _打开记录(self):
        # 开在主窗的标签页里，而不是丢给系统默认程序 ——
        # 不依赖 .md 文件关联，也不会突然弹个记事本盖住界面。
        路径 = getattr(self.主窗, "_找文档", None)
        候选 = 路径("版本记录.md") if 路径 else None
        if not 候选:
            候选 = os.path.join(这里, "版本记录.md")
        if os.path.isfile(候选):
            self.主窗.打开(候选)
        else:
            self.主窗.状态("找不到 版本记录.md")


class 关于对话框(QDialog):
    """关于核工坊。

    和设置窗口的「关于」页分工不同：那边讲**语言规模**（各类写法条数），
    这边讲**运行环境**（内核、Python、后缀、仓库地址），内容不重复。
    """

    def __init__(self, 主窗, 内核版本):
        super().__init__(主窗)
        self.主窗 = 主窗
        self.内核版本 = 内核版本
        self.setWindowTitle("关于核工坊")
        self.setModal(False)
        self.resize(460, 320)
        self.setStyleSheet(主窗.styleSheet())
        self.跟主题 = True
        self._建界面()

    def _建界面(self):
        布局 = QVBoxLayout(self)
        布局.setContentsMargins(24, 22, 24, 18)
        布局.setSpacing(8)

        标 = QLabel("核工坊")
        标.setObjectName("aboutTitle")
        布局.addWidget(标)

        副 = QLabel("用中文写程序 · 源文件后缀 %s" % self.主窗.内核.扩展名)
        副.setObjectName("hintText")
        布局.addWidget(副)

        布局.addSpacing(10)
        内核文件 = "核.py"
        条目 = [
            ("界面版本", "v%s（Qt 版）" % self.内核版本),
            ("内核版本", "v%s" % self.主窗.内核.版本),
            ("Python", sys.version.split()[0]),
            ("源文件后缀", self.主窗.内核.扩展名),
            ("内核文件", 内核文件),
        ]
        for 名, 值 in 条目:
            行 = QHBoxLayout()
            左 = QLabel(名)
            左.setFixedWidth(84)
            行.addWidget(左)
            值标 = QLabel(str(值))
            值标.setTextInteractionFlags(Qt.TextSelectableByMouse)
            行.addWidget(值标)
            行.addStretch(1)
            布局.addLayout(行)

        布局.addSpacing(8)
        链 = QLabel("github.com/xiaohetaoo/he-language")
        链.setObjectName("linkLabel")
        链.setCursor(Qt.PointingHandCursor)
        链.setToolTip("打开项目主页")
        链.mousePressEvent = lambda e: self._打开("https://github.com/xiaohetaoo/he-language")
        布局.addWidget(链)

        链2 = QLabel("查看最新版本与下载 →")
        链2.setObjectName("linkLabel")
        链2.setCursor(Qt.PointingHandCursor)
        链2.mousePressEvent = lambda e: self._打开(
            "https://github.com/xiaohetaoo/he-language/releases"
        )
        布局.addWidget(链2)

        布局.addStretch(1)

        行2 = QHBoxLayout()
        行2.addStretch(1)
        钮 = QPushButton("关闭")
        钮.setAutoDefault(False)
        钮.setProperty("primary", "true")
        钮.clicked.connect(self.close)
        行2.addWidget(钮)
        布局.addLayout(行2)

    def _打开(self, 地址):
        try:
            os.startfile(地址)
        except Exception as e:  # noqa: BLE001
            self.主窗.状态("打不开浏览器：%s" % e)
