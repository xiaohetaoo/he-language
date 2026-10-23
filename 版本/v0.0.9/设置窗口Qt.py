# -*- coding: utf-8 -*-
"""核工坊 Qt 版设置对话框（外观 / 编辑器 / 运行 / 关于 四页）。"""

import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QSlider, QStackedWidget, QVBoxLayout, QWidget,
)

import 主题

这里 = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, 这里)

import 核  # noqa: E402
from 核工坊Qt import 带箭头下拉框  # noqa: E402


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
            "自动高亮": 主窗.自动高亮,
        }

        self.setWindowTitle("设置")
        self.setModal(True)
        self.resize(720, 560)
        # 独立窗口不会自动继承父窗口样式，必须显式套一份
        self.setStyleSheet(
            主题.生成样式(主窗.主题, 主窗.字号, 主窗.等宽字体名())
        )
        if os.path.exists(os.path.join(这里, "素材", "核图标.ico")):
            from PySide6.QtGui import QIcon

            self.setWindowIcon(QIcon(os.path.join(这里, "素材", "核图标.ico")))

        self._建界面()
        self._同步箭头色()

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
        self.标题.setObjectName("pageTitle")
        右布局.addWidget(self.标题)

        self.说明 = QLabel("")
        self.说明.setObjectName("hintText")
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
        self.按钮们 = {}
        for 文本, 槽, 主要 in (
            ("确定", self.确定, True),
            ("应用", self.应用, False),
            ("取消", self.取消, False),
        ):
            钮 = QPushButton(文本)
            # 关键：要设 autoDefault=False。
            # Qt 对话框里按钮默认 autoDefault=True，一旦有焦点就会成为
            # 「默认按钮」：实测对话框 show 之后 Qt 把默认转给了「更改…」，
            # 于是它变成蓝色主按钮，而且按回车会去弹文件选择框 —— 真 bug。
            钮.setAutoDefault(False)
            钮.setDefault(bool(主要))
            # 主按钮样式用自定义属性控制，不依赖 Qt 的 :default 状态：
            # 那个状态会被 Qt 自己改，颜色就飘走了。
            if 主要:
                钮.setProperty("primary", "true")
            钮.clicked.connect(槽)
            按钮布局.addWidget(钮)
            self.按钮们[文本] = 钮
        右布局.addWidget(按钮行)

        外层.addWidget(右, 1)
        self.左栏.setCurrentRow(0)
        self._切页(0)
        # 全部控件建完之后再确认一次默认按钮，避免被后续 setFocus 抢走
        self.按钮们["确定"].setDefault(True)
        self.按钮们["确定"].setFocus()

    def _分组(self, 文本):
        标 = QLabel(文本)
        标.setObjectName("groupTitle")
        return 标

    def _页外观(self):
        页 = QWidget()
        布局 = QVBoxLayout(页)
        布局.setContentsMargins(0, 0, 0, 0)
        布局.setSpacing(10)

        布局.addWidget(self._分组("配色"))
        行 = QHBoxLayout()
        self.主题框 = 带箭头下拉框()
        for 名 in 主题.主题集:
            self.主题框.addItem(名)
        self.主题框.setCurrentText(self.主窗.主题名)
        self.主题框.currentTextChanged.connect(self._换主题)
        行.addWidget(self.主题框)
        行.addStretch(1)
        布局.addLayout(行)

        布局.addWidget(self._分组("编辑器字号"))
        字号行 = QHBoxLayout()
        字号行.setSpacing(10)
        # 用滑动条而不是下拉框：
        #   · 下拉列表要枚举所有值，范围一大列表就长得没法看；
        #   · 拖动能连续看到效果，比「选中→看变化」直观得多。
        self.字号条 = QSlider(Qt.Horizontal)
        self.字号条.setMinimum(主题.字号最小)
        self.字号条.setMaximum(主题.字号最大)
        self.字号条.setSingleStep(主题.字号步长)
        self.字号条.setPageStep(2)
        self.字号条.setTickPosition(QSlider.TicksBelow)
        self.字号条.setTickInterval(4)
        self.字号条.setValue(主题.夹字号(self.主窗.字号))
        # 拖动时 valueChanged 会连续触发，是想要的（实时预览）；
        # 但每次都要重建整份样式表，太重 —— 见 _换字号 里的去抖。
        self.字号条.valueChanged.connect(self._换字号)
        # 松手立刻落实最后一个值，不等去抖
        self.字号条.sliderReleased.connect(self._字号松手)
        字号行.addWidget(self.字号条, 1)
        # 当前值单独显示，拖动时眼睛不用在刻度上找
        self.字号标 = QLabel("%d pt" % self.字号条.value())
        self.字号标.setFixedWidth(52)
        self.字号标.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.字号标.setObjectName("sliderValue")
        字号行.addWidget(self.字号标)
        布局.addLayout(字号行)

        字号范围 = QLabel(
            "范围 %d–%d pt　·　代码区域的字号，行号栏会跟着缩放"
            % (主题.字号最小, 主题.字号最大)
        )
        字号范围.setObjectName("hintText")
        布局.addWidget(字号范围)

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
        self.缩进框 = 带箭头下拉框()
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
        # 这个勾选框以前根本没连信号 —— 点它什么也不会发生，
        # 用户看到的就是「设置应用不能马上生效」。
        self.勾高亮.stateChanged.connect(self._换高亮)
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
        # 不设 autoDefault：否则它会在对话框显示时抢走「默认按钮」，
        # 按回车就弹文件选择框，而不是确认设置。
        改.setAutoDefault(False)
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
        标.setObjectName("aboutTitle")
        布局.addWidget(标)
        布局.addWidget(
            QLabel("用中文写程序 · 源文件后缀 %s" % 核.扩展名)
        )

        布局.addSpacing(10)
        # 这里统计的是「中文写法条数」，不是 Python 侧去重后的种类数：
        # 一个英文关键字可以有两种写法（in → 核在 / 遍历），
        # 异常更是大量别名（IndexError 既是 下标错误 也是 越界错误）。
        # 用户会拿这个数字和对照表比，所以下面补一句口径说明。
        for 名, 值 in (
            ("关键字写法", len(核.关键词表)),
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

        说明 = QLabel(
            "上面的数字是「中文写法条数」。一个英文关键字可以对应多种写法"
            "（in 既是 核在 也是 遍历），异常也有别名，"
            "所以按英文去重后的种类数会比这里少。"
        )
        说明.setWordWrap(True)
        说明.setObjectName("hintText")
        布局.addSpacing(4)
        布局.addWidget(说明)

        布局.addSpacing(14)
        链 = QLabel("查看最新版本与下载 → github.com/xiaohetaoo/he-language/releases")
        链.setObjectName("linkLabel")
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
        # 对话框是独立窗口，不会自动跟主窗换皮，得自己再套一次
        self.setStyleSheet(
            主题.生成样式(
                self.主窗.主题, self.主窗.字号, self.主窗.等宽字体名()
            )
        )
        self._同步箭头色()

    def _同步箭头色(self):
        """下拉框的三角箭头是自绘的，换主题后要跟着改色。"""
        色 = self.主窗.主题["次要文本"]
        for 框 in (getattr(self, "主题框", None), getattr(self, "字号框", None),
                   getattr(self, "缩进框", None)):
            if 框 is not None and hasattr(框, "设箭头色"):
                框.设箭头色(色)

    def _换字号(self, 值):
        """拖动滑动条时实时应用。

        拖一次会连续触发很多次 valueChanged，每次都要重建整份样式表
        （几百条 QSS 规则 + 所有文档重新设字体），开销不小。
        用 30ms 去抖把连续事件合成一次：拖动过程中最多每 30ms 应用一次，
        松手后立刻生效。标签是立刻更新的 —— 它只改一个数字，可以忽略。
        """
        self.字号标.setText("%d pt" % 值)
        self._待应用字号 = int(值)
        任务 = getattr(self, "_字号任务", None)
        if 任务 is None:
            from PySide6.QtCore import QTimer

            任务 = QTimer(self)
            任务.setSingleShot(True)
            任务.setInterval(30)
            任务.timeout.connect(self._落实字号)
            self._字号任务 = 任务
        任务.start(30)

    def _落实字号(self):
        值 = getattr(self, "_待应用字号", None)
        if 值 is not None:
            self.主窗.设字号(值)

    def _字号松手(self):
        """松开滑动条：把最后一次待应用的值立刻落实。

        拖动过程中靠 30ms 去抖，最后一个值可能还在定时器里没执行；
        用户松手时应该马上看到最终效果，不能再等 30ms。
        """
        任务 = getattr(self, "_字号任务", None)
        if 任务 is not None:
            任务.stop()
        self._落实字号()

    def _换行号(self, _状态):
        self.主窗.设行号(self.勾行号.isChecked())

    def _换缩进线(self, _状态):
        self.主窗.设缩进线(self.勾缩进线.isChecked())

    def _换制表宽(self, _索引):
        n = self.缩进框.currentData()
        if n:
            self.主窗.设制表宽(int(n))

    def _换高亮(self, _状态):
        self.主窗.设自动高亮(self.勾高亮.isChecked())

    def _选目录(self):
        from PySide6.QtWidgets import QFileDialog

        目录 = QFileDialog.getExistingDirectory(self, "选择项目文件夹", self.主窗.项目目录)
        if 目录:
            self.目录框.setText(目录)
            # 立刻换项目树，而不是等下一次启动
            self.主窗.装载项目树(目录)
            self.主窗.应用设置(保存=True)
            self.主窗.状态("项目：%s" % 目录)

    def _打开发布页(self):
        地址 = "https://github.com/xiaohetaoo/he-language/releases"
        try:
            os.startfile(地址)
        except Exception:
            self.主窗.状态("打不开浏览器：%s" % 地址)

    # —— 提交 ——

    def 应用(self):
        """确认所有改动：立刻生效并写盘。

        以前这里只把 结果 置 True、喊一句「已应用」，既不推给编辑器
        也不写盘 —— 所以用户必须关掉软件重开才看得到效果。
        """
        # 先把拖动去抖里还没落实的字号补上，否则快速拖完立刻按确定，
        # 最后一次的值可能还躺在定时器里没生效。
        self._落实字号()
        self.结果 = True
        self.主窗.应用设置(保存=True)
        self.主窗.状态("设置已应用")

    def 确定(self):
        self.应用()
        self.关闭()

    def 取消(self):
        """把预览过的改动全部还原。

        每一项都要还原：以前只还原了主题和字号，行号/缩进线/高亮
        留在被改过的状态，按「取消」等于没取消。
        """
        主窗 = self.主窗
        # 停掉字号去抖，否则还原之后定时器又把它改回去
        任务 = getattr(self, "_字号任务", None)
        if 任务 is not None:
            任务.stop()
        self._待应用字号 = None
        if 主窗.主题名 != self.原始["主题名"]:
            主窗.换主题(self.原始["主题名"])
        主窗.设字号(self.原始["字号"])
        # 滑动条也要回到原值，不然界面显示的仍是刚拖到的位置
        条 = getattr(self, "字号条", None)
        if 条 is not None:
            条.blockSignals(True)
            条.setValue(主题.夹字号(self.原始["字号"]))
            条.blockSignals(False)
            标 = getattr(self, "字号标", None)
            if 标 is not None:
                标.setText("%d pt" % 条.value())
        主窗.设制表宽(self.原始["制表宽"])
        主窗.设缩进线(self.原始["缩进线"])
        主窗.设行号(self.原始["行号"])
        主窗.设自动高亮(self.原始["自动高亮"])
        主窗.应用设置(保存=True)
        主窗.状态("设置已取消")
        self.结果 = False
        self.关闭()

    def 关闭(self):
        """安全关闭对话框。

        用 close() 而不是 destroy()：destroy() 会直接销毁底层对象，
        在 exec() 的模态循环里可能让循环拿不到返回值、表现为卡住。
        先 close() 结束模态，再 deleteLater() 交给事件循环回收。
        """
        self.close()
        self.deleteLater()
