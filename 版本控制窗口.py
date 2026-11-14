# -*- coding: utf-8 -*-
"""版本控制面板（Qt 版，**只读**）。

只展示「当前分支 / 有哪些文件改过 / 与上游差几个提交」，
双击一行把那个文件在编辑器里打开。

**刻意不做提交、暂存、推送** —— 原因写在 版本控制.py 的模块注释里：
推送有硬约定，界面上的按钮会变成绕过约定的快捷路径。
这里给一句提示，让想提交的人知道该去哪儿做。
"""

import os

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QSplitter,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout,
)

import 主题
import 版本控制


def 等宽字体():
    """挑一个系统上真实存在的等宽字体。

    diff 必须等宽，否则 `-` / `+` 开头的行对不齐。
    先问 QFontDatabase 要一个可用的族名，都没有就退回 QFont 的等宽风格 ——
    不能凭名字猜：名字不存在时 Qt 会静默替换成默认字体，
    等宽对齐就悄悄失效了（看不出报错，只是看着歪）。

    **候选表统一从 主题 取**（0.2.7 修）：以前这里自己抄了一份，
    比 主题.等宽候选 少了 JetBrains Mono、多了 DejaVu Sans Mono。
    于是同一台机器上编辑器用 Cascadia、diff 用 DejaVu —— 两边行高不一致，
    diff 里 `+`/`-` 行与上下文的间距也对不齐，看着就是「没对齐」。
    现在两者共用一份：编辑器挑到哪个，diff 就用哪个。
    字号也跟编辑器走（主窗字号），不再写死 10。
    """
    import 主题

    from PySide6.QtGui import QFontDatabase

    候选 = 主题.等宽候选
    已装 = set(QFontDatabase.families())
    for 名 in 候选:
        if 名 in 已装:
            return 名
    return 候选[-1]


def 等宽字体对象(主窗=None):
    """等宽 QFont（带字号），给 diff 预览用。"""
    from PySide6.QtGui import QFont

    字号 = int(getattr(主窗, "字号", 12)) if 主窗 is not None else 12
    字体 = QFont(等宽字体(), 字号)
    字体.setStyleHint(QFont.Monospace)
    return 字体



class 版本控制窗口(QDialog):
    def __init__(self, 主窗, 目录):
        super().__init__(主窗)
        self.主窗 = 主窗
        self.目录 = 目录
        self.setWindowTitle("版本控制")
        self.setModal(False)
        self.resize(620, 460)
        self.setStyleSheet(主窗.styleSheet())
        # 主窗换主题时由 核工坊Qt.主窗._同步对话框样式 重新套一遍
        self.跟主题 = True
        self._建界面()
        # 第一次读同步做：面板一建出来就该是填好的状态。
        # 之后用户点「刷新」按钮才走后台线程（见 刷新 的说明）。
        self._建成 = True
        self.刷新(同步=True)

    def _建界面(self):
        布局 = QVBoxLayout(self)
        布局.setContentsMargins(主题.内边距, 主题.内边距, 主题.内边距, 主题.内边距)
        布局.setSpacing(主题.间距)

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
        # 选中即预览：单击一行就把它摆到下面的 diff 区里看。
        # 双击留给「在编辑器里打开」—— 两件事分开，不会互相抢。
        self.树.currentItemChanged.connect(self._选中变化)

        # —— diff 预览 ——
        #
        # 以前面板只列「哪些文件改了」，想知道改了什么只能去命令行。
        # 现在点一行就能看只读 diff。**仍然只读**：没有暂存、提交、推送的
        # 任何入口（原因见 版本控制.py 的模块说明 —— 推送有硬约定）。
        self.差异 = QPlainTextEdit()
        self.差异.setObjectName("diffView")
        self.差异.setReadOnly(True)
        self.差异.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.差异.setFont(等宽字体对象(self.主窗))
        self.差异.setPlaceholderText("选中上面的文件，这里显示它的差异")

        分栏 = QSplitter(Qt.Vertical)
        分栏.addWidget(self.树)
        分栏.addWidget(self.差异)
        分栏.setSizes([200, 260])
        分栏.setChildrenCollapsible(False)
        布局.addWidget(分栏, 1)
        self._分栏 = 分栏


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

    def 刷新(self, 同步=None):
        """重新读一次仓库状态。

        **点「刷新」按钮走后台线程**（0.2.7 修）。以前这里直接同步调
        版本控制.状态()，会串行跑 4 个 git 子进程（每个超时 6 秒）。
        主窗顶部那个按钮早就改成后台查了（见 版本查询器），
        但面板自己的「刷新」漏了 —— 大仓库、网络盘、或杀毒软件
        逐个文件扫描时，点一下刷新整个界面就白屏几秒。
        这里复用主窗的 版本查询器（同一时刻只允许一个查询在飞，
        连点不会堆出并发子进程）。

        `同步` 参数：构造时（`__init__` 里那次）要**同步**读 ——
        面板刚建出来就必须是填好的状态，否则打开面板先看到一瞬间空白，
        而且调用方（测试、以及任何「建完立刻读」的代码）拿到的是空表。
        用户点「刷新」按钮时才走异步。
        """
        if 同步 is None:
            同步 = not getattr(self, "_建成", False)
        self.树.clear()
        self.概要.setText("正在读取版本控制状态…")
        self.空提示.setText("")
        差异 = getattr(self, "_差异", None)
        if 差异 is not None:
            差异.clear()
        查询器 = getattr(self.主窗, "_版本查询", None)
        if 同步 or 查询器 is None:
            # 没有查询器（单测里直接 new 面板、或面板先于主窗就绪）也走同步：
            # 功能不能缺，只是这一次会卡一下。
            self._状态回来了(版本控制.状态(self.目录), self.目录)
            return
        # 只连接一次：面板存活期间会反复点「刷新」，
        # 每点一次都 connect 会让回调被调 N 次（Qt 不会自动去重，
        # UniqueConnection 要求带 Qt.ConnectionType 组合，写起来反而易错）。
        if not getattr(self, "_已接信号", False):
            try:
                查询器.好了.connect(self._状态回来了)
                self._已接信号 = True
            except (RuntimeError, TypeError):
                self._已接信号 = False
        查询器.查(self.目录)

    def _状态回来了(self, 状态, 目录):
        """后台查询结果回来了（主线程执行）。"""
        if 目录 != self.目录:
            return  # 期间换了目录，这次结果过期
        try:
            self._填状态(状态)
        except RuntimeError:
            pass  # 面板已经关掉了

    def _填状态(self, 状态):
        self.状态 = 状态
        self.树.clear()
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
                "单击一行看差异，双击在编辑器里打开。"
                "本面板只做展示 —— 提交与推送请在命令行或 git 客户端里进行"
                "（推送前需要确认）。"
            )
        else:
            self.空提示.setText("工作区干净，没有未提交的改动。")

    # —— diff 预览 ——

    def _选中变化(self, 现在, _以前):
        """选中某一行 → 把它的差异摆到下面。

        读 diff 会在 GUI 线程上跑一条 git 子进程（小文件实测十几毫秒，
        大文件能到几百毫秒）。这里用 0 延时单发延后一拍再做：
        用户连按方向键换选时，中间那些选区不会各触发一次 git 调用，
        只有停下来之后那一次真正执行 —— 既不用起后台线程，也不会卡手。
        """
        self._待看 = 现在.data(0, Qt.UserRole) if 现在 is not None else None
        if 现在 is None:
            self.差异.clear()
            return
        # 复用同一个定时器。
        # 以前每次换选都新建一个 QTimer(self)，把旧的 stop() 掉就不再管 ——
        # stop 只停计时、不销毁对象，而它的父窗口一直活着，于是方向键
        # 上下翻 N 次就积 N 个 QTimer（实测换选 5 次漏 5 个）。
        任务 = getattr(self, "_看延时", None)
        if 任务 is None:
            任务 = QTimer(self)
            任务.setSingleShot(True)
            任务.timeout.connect(self._显示差异)
            self._看延时 = 任务
        任务.start(0)

    def _显示差异(self):
        相对 = getattr(self, "_待看", None)
        if not 相对:
            self.差异.clear()
            return
        文本, 说明 = 版本控制.取差异(self.目录, 相对)
        if not 文本:
            self.差异.setPlainText(说明 or "没有可显示的差异")
            return
        if 说明:
            self.差异.setPlainText("核核 %s\n%s" % (说明, 文本))
        else:
            self.差异.setPlainText(文本)
        self._上色()
        # 回到顶部：大 diff 打开时停在文末会让人以为「什么都没变」
        游 = self.差异.textCursor()
        游.movePosition(QTextCursor.Start)
        self.差异.setTextCursor(游)

    def 重套样式(self):
        """主窗换主题时被调用：除了换样式表，还要按新色表重新给 diff 上色。

        为什么必须重染：diff 的增/删底色是 逐行 QTextCharFormat ，
        不是 QSS —— 换主题时 QSS 会自动跟着换，但已经写进字符格式的
        颜色不会，于是浅色主题下 diff 还是深色主题的淡绿淡红。

        顺带把等宽字体按主窗的**当前字号**重设一次（0.2.7 补）：
        字体是在构造时按当时的字号建的，之后用户改了字号，
        主窗只遍历 文档集 调 设置字体，从不会碰到这个面板 ——
        于是编辑器字号变了、diff 还是老字号，两块的字距对不上。
        """
        self.setStyleSheet(self.主窗.styleSheet())
        try:
            self.差异.setFont(等宽字体对象(self.主窗))
        except (AttributeError, RuntimeError):
            pass
        self._上色()

    def _上色(self):
        """按行首符号给 diff 上色：+ 绿、- 红、@@ 蓝、其余不动。

        色值一律从主题表取（换主题要跟着换），不写死 ——
        否则切到浅色主题后，深色主题的淡绿底会把浅色界面糊成一片。

        用 QTextCursor 逐块设字符格式，不碰 QSS：
        QSS 没法按「行首是什么字符」区分，只能整块一个前景色。
        """
        表 = getattr(self.主窗, "主题", {}) or {}
        增底 = 表.get("diff增底")
        删底 = 表.get("diff删底")
        增字 = 表.get("diff增字")
        删字 = 表.get("diff删字")
        头字 = 表.get("diff头字")
        文档 = self.差异.document()
        块 = 文档.firstBlock()
        while 块.isValid():
            文本 = 块.text()
            底 = 字 = None
            if 文本.startswith("+++") or 文本.startswith("---") or 文本.startswith("@@"):
                # 文件头与 hunk 头：用强调色，不给底色（它们不是增删内容）
                字 = 头字
            elif 文本.startswith("+"):
                底, 字 = 增底, 增字
            elif 文本.startswith("-"):
                底, 字 = 删底, 删字
            if 字 or 底:
                游 = QTextCursor(块)
                游.select(QTextCursor.BlockUnderCursor)
                格式 = QTextCharFormat()
                if 字:
                    格式.setForeground(QColor(字))
                if 底:
                    格式.setBackground(QColor(底))
                游.mergeCharFormat(格式)
            块 = 块.next()

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
