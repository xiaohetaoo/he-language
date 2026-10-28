# -*- coding: utf-8 -*-
"""核工坊的代码编辑器控件（PySide6 版）。

包含：行号栏、当前行高亮、缩进参考线、语法高亮、自动缩进、
      注释切换、查找定位。

与 tkinter 版行为一致，但代码量少很多 —— 高亮、选区、撤销栈都由 Qt 提供。
"""

import re

from PySide6.QtCore import QPoint, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor, QFont, QFontDatabase, QFontMetrics, QPainter, QPen, QTextBlockUserData,
    QTextCharFormat, QTextCursor, QSyntaxHighlighter, QKeyEvent,
)
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget

import 核
import 主题


def 挑等宽字体():
    """挑一个系统里有的等宽字体。"""
    已有 = set(QFontDatabase.families())
    for 名 in 主题.等宽候选:
        if 名 in 已有:
            return 名
    return "Courier New"


# ---------------------------------------------------------------------------
# 语法高亮
# ---------------------------------------------------------------------------


class 高亮器(QSyntaxHighlighter):
    """核语言语法高亮。

    词表从 核.py 的对照表动态取，内核扩了对照表这里自动跟着变。
    规则顺序即优先级：注释、字符串要压过其他规则。
    """

    def __init__(self, 文档, 主窗):
        super().__init__(文档)
        self.主窗 = 主窗
        # 总开关：设置里勾掉「输入时自动语法高亮」就置 False。
        # 只断开重建不够 —— 规则已挂上就会一直染色，必须让 highlightBlock
        # 直接返回，再 rehighlight 一次把颜色洗掉。
        self.开 = bool(getattr(主窗, "自动高亮", True))
        self.规则 = []
        self.重建()

    def 重建(self):
        内核 = self.主窗.内核
        主题色 = self.主窗.主题

        def 格式(色, 粗体=False, 斜体=False):
            f = QTextCharFormat()
            f.setForeground(QColor(色))
            if 粗体:
                f.setFontWeight(QFont.Bold)
            if 斜体:
                f.setFontItalic(True)
            return f

        # 注意：这里不把「核核」算进关键字 —— 它是注释引导词，
        # 由 _标注释 单独染色。混进关键字表会被关键字规则先染一遍，
        # 与注释色打架（而且判定口径还不一样）。
        关键字 = sorted(set(内核.关键词表), key=len, reverse=True)
        内置 = sorted(
            set(内核.函数表) | set(内核.方法表), key=len, reverse=True
        )

        def 带边界(词):
            return r"(?<![\w\u4e00-\u9fff])(?:%s)(?![\w\u4e00-\u9fff])" % "|".join(
                词
            )

        # 注释格式单独存：注释不走正则（见下面 _标注释 的说明），
        # 但仍要用同一套配色，所以在这里建好放进 self.注释格式。
        self.注释格式 = 格式(主题色["注释"], 斜体=True)
        self.字符串格式 = 格式(主题色["字符串"])

        self.规则 = [
            # 注释和字符串都不在这里 —— 「核核」的判定必须与 核.py 翻译器
            # **完全一致**，一条正则只能表达「任意位置匹配」，两者在
            # 「核核abc 核核 def」这种行上必然打架；字符串还会跨行。
            # 两者都交给 核.扫描行 一次扫出来（见 highlightBlock）。
            #
            # 更要紧的是「后染的覆盖先染的」：以前规则按列表顺序
            # finditer + setFormat，字符串规则排第一，关键字/内置/数字
            # 排在后面，于是 核说("核若 核长度") 里字符串**内部**的
            # 「核若」「核长度」被关键字色、内置色盖掉 —— 字符串看着像代码。
            # 现在字符串、注释由 扫描行 定出区间，其余规则跳过区间内的命中，
            # 最后再统一染一遍字符串，优先级不再依赖列表顺序。
            (r"\b0[xX][0-9a-fA-F]+\b|\b\d[\d_]*(?:\.\d+)?\b", 格式(主题色["数字"])),
            (带边界(关键字), 格式(主题色["关键字"], 粗体=True)),
            (带边界(内置), 格式(主题色["内置"])),
            (r"(?<=核定义\s)[^\s(（:：]+", 格式(主题色["函数名"], 粗体=True)),
            (r"(?<=核类\s)[^\s(（:：]+", 格式(主题色["函数名"], 粗体=True)),
        ]

    def _标注释(self, 文本, 格式, 注释起):
        """把注释放到行尾染成注释色。

        注释起 由 核.扫描行 给出（-1 表示本行没有注释）—— 判定直接用
        核.py 自己的扫描器，和翻译器同一套规则，不会再出现
        「高亮说是注释、翻译说是代码」；字符串里的「核核」也不会被误认
        （扫描器碰到字符串会整段跳过）。
        """
        if 注释起 is not None and 注释起 >= 0:
            self.setFormat(注释起, len(文本) - 注释起, 格式)

    def highlightBlock(self, 文本):
        if not self.开:
            # 关闭高亮时也要把块状态归零，否则下次打开会读到陈旧状态，
            # 把一整块凭空当成三引号串的续行。
            self.setCurrentBlockState(0)
            return
        核 = self.主窗.内核
        # 块状态：0 = 正常，1 = 在 ''' 里，2 = 在 \"\"\" 里。
        # 用 QSyntaxHighlighter 自己的 setCurrentBlockState —— 这是 Qt 为此
        # 准备的接口；自定义块数据（折叠标记）走 QTextBlockUserData，
        # 两者互不干扰。注意首块 previousBlockState() 是 -1，按 0 处理。
        上态 = self.previousBlockState()
        起始引号 = None
        if 上态 == 1:
            起始引号 = "'''"
        elif 上态 == 2:
            起始引号 = '"""'

        串区, 注释起, 未闭合 = 核.扫描行(文本, 起始引号)
        if 未闭合 == "'''":
            self.setCurrentBlockState(1)
        elif 未闭合 == '"""':
            self.setCurrentBlockState(2)
        else:
            self.setCurrentBlockState(0)
        if 注释起 is not None and 注释起 < 0:
            注释起 = None

        def 在串里(位置):
            return any(起 <= 位置 < 止 for 起, 止 in 串区)

        def 在注释里(位置):
            return 注释起 is not None and 位置 >= 注释起

        for 模式, 格式 in self.规则:
            for m in re.finditer(模式, 文本):
                起 = m.start()
                # 字符串和注释里的内容不属于代码，任何规则都不该染上去。
                # 注释这一条以前漏了：核核 核说(1) 核若 123 里的
                # 「核说」「核若」「123」会被染成内置色/关键字色/数字色，
                # 一条注释看起来花花绿绿像代码 —— 和字符串那条是同一个毛病。
                if 在串里(起) or 在注释里(起):
                    continue
                self.setFormat(起, m.end() - 起, 格式)
        # 注释与字符串最后染：它们是最高优先级，任何规则都不该盖到头上。
        self._标注释(文本, self.注释格式, 注释起 if 注释起 is not None else -1)
        for 起, 止 in 串区:
            self.setFormat(起, 止 - 起, self.字符串格式)


# ---------------------------------------------------------------------------
# 行号栏
# ---------------------------------------------------------------------------


class 折叠数据(QTextBlockUserData):
    """挂在块上的折叠标记。

    为什么不用 QTextBlock.setUserState()：
    **userState 被 QSyntaxHighlighter 内部占用** —— Qt 每次重新高亮都会
    把上一块的 userState 往下一块传播（默认值 -1，即所有位都是 1）。
    用一个位当折叠标记会和它打架：新文档里每一块都「看起来已折叠」；
    而高亮一跑，真正的折叠标记又会被传播过来的值冲掉。
    QTextBlockUserData 才是 Qt 给「用户自己的块级数据」准备的位置，
    高亮器不碰它，且它会跟着块一起在编辑中搬运。
    """

    __slots__ = ("折叠", "区头文本", "区止块", "区界块")

    def __init__(self):
        super().__init__()
        self.折叠 = False
        # 折叠区缓存。折叠区() 要向下扫到区域结束，800 个并列折叠头
        # 实测一次全文重算 32ms —— 是「有折叠时每敲一键重算全文」里
        # 最贵的一项。而区域边界只由「本行的缩进与行尾冒号」和
        # 「区域外第一个缩进不深于本行的行」两处决定，只要这两处没被
        # 改到，缓存就依然成立（见 折叠区 / _缓存边界）。
        self.区头文本 = None    # 建缓存时本行的文本
        self.区止块 = None      # 区域最后一块
        self.区界块 = None      # 让区域停下来的那一块（None = 一直到最后）


class 行号区(QWidget):
    #: 折叠三角占用的左边距（像素）。行号是右对齐的，两者不会打架。
    折叠栏宽 = 16

    def __init__(self, 编辑器):
        super().__init__(编辑器)
        self.编辑器 = 编辑器
        # 给 QSS 一个钩子：行号栏是 QWidget 子类，会被全局 QWidget 的
        # font-size 覆盖，必须靠 #gutter 规则才能跟正文字号一致。
        self.setObjectName("gutter")
        # 宽度按「最大行号位数」自适应，至少 3 位（58px）。
        # 太窄时两位数就挤到边缘，正文看起来像被行号压住了。
        self.宽度 = 58
        self.setFixedWidth(self.宽度)
        # 折叠三角的悬停高亮：移上去变亮，让用户知道这里能点
        self._悬停块 = -1
        self.setMouseTracking(True)

    def 按行号调整宽度(self, 总行数):
        """按「最大行号位数」和当前字体的实际字宽算宽度。

        以前是 `16 + 位数*9`，9 这个系数只在小字号下凑巧够用：
        字号调到 20/22 时，三位数字实测要 35~39px，而宽度仍是 43，
        减掉右边距 10 就只剩 33 —— 数字被裁掉一部分，
        看起来就像行号「缺了一半」。
        """
        位数 = max(3, len(str(max(1, 总行数))))
        fm = self.fontMetrics()
        数字宽 = fm.horizontalAdvance("8" * 位数)
        # 10 = 右边距（paintEvent 里 drawText 用的是 宽度-10）
        新宽 = max(28, 数字宽 + 10 + 8)
        if 新宽 != self.宽度:
            self.宽度 = 新宽
            self.setFixedWidth(新宽)
            return True
        return False

    def sizeHint(self):
        return QSize(self.宽度, 0)

    def paintEvent(self, 事件):
        色 = self.编辑器.主窗.主题
        绘 = QPainter(self)
        绘.fillRect(self.rect(), QColor(色["行号底"]))
        绘.setFont(self.编辑器.font())

        编辑器 = self.编辑器
        块 = 编辑器.firstVisibleBlock()
        号 = 块.blockNumber() + 1
        # 坐标换算（这里错过两次，两次都表现为「行标是歪的」）：
        #   blockBoundingGeometry 给的是**内容坐标**；加 contentOffset() 后
        #   得到的是**视口坐标**，而不是行号栏自己的坐标。
        #   行号栏和视口同属编辑器，但左上角并不重合：视口被 setViewportMargins
        #   推到行号栏右边，视口上方还有样式表的 padding-top。
        #   所以必须补上「视口 y - 行号栏 y」这个差。
        #   上一版减的是 self.y()——行号栏的 y 恰好等于它自己的内边距（6px），
        #   相当于把行号整体上移 6px，用户看到的就是行标歪、和正文对不齐。
        偏移 = 编辑器.viewport().y() - self.y()
        顶 = (
            int(
                编辑器.blockBoundingGeometry(块)
                .translated(编辑器.contentOffset())
                .top()
            )
            + 偏移
        )

        while 块.isValid() and 顶 <= 事件.rect().bottom():
            高 = int(编辑器.blockBoundingRect(块).height())
            if 块.isVisible() and 顶 + 高 >= 事件.rect().top():
                # 当前行的行号用正文色，其余用行号灰（与 PyCharm 一致）；
                # 眼睛跟着光标走时能立刻找到「我在第几行」。
                if 块.blockNumber() == 编辑器.当前行号():
                    绘.setPen(QPen(QColor(色["文本"])))
                else:
                    绘.setPen(QPen(QColor(色["行号字"])))
                # 矩形高度用这一块的实际高度，垂直居中交给 AlignVCenter。
                # 换字体（Cascadia/Consolas 行高不同）也不会错位。
                绘.drawText(
                    0, 顶, self.宽度 - 10, 高,
                    Qt.AlignRight | Qt.AlignVCenter, str(号),
                )
                if 编辑器.可折叠(块):
                    self._画折叠三角(绘, 块, 顶, 高, 色)
            块 = 块.next()
            顶 += 高
            号 += 1

    def _画折叠三角(self, 绘, 块, 顶, 高, 色):
        """在行号左侧画折叠三角：展开是 ▼，已折叠是 ▶。"""
        展开 = not self.编辑器.已折叠(块)
        色键 = "行号字"
        if 块.blockNumber() == self._悬停块:
            色键 = "文本"          # 悬停时变亮，提示可点
        绘.setPen(Qt.NoPen)
        绘.setBrush(QColor(色.get(色键, 色["行号字"])))
        中 = 顶 + 高 // 2
        if 展开:
            # ▼ 向下的三角
            绘.drawPolygon([
                QPoint(4, 中 - 3), QPoint(11, 中 - 3), QPoint(7, 中 + 3),
            ])
        else:
            # ▶ 向右的三角
            绘.drawPolygon([
                QPoint(5, 中 - 4), QPoint(5, 中 + 4), QPoint(12, 中),
            ])
        绘.setBrush(Qt.NoBrush)

    def 折叠三角处(self, 位置):
        """这个坐标是不是落在某个折叠三角上？是则返回块，否则 None。"""
        if 位置.x() > self.折叠栏宽:
            return None
        块 = self.编辑器._块在y(位置.y())
        if 块 is None or not 块.isVisible():
            return None
        return 块 if self.编辑器.可折叠(块) else None

    def mousePressEvent(self, 事件):
        if 事件.button() == Qt.LeftButton:
            块 = self.折叠三角处(事件.position().toPoint())
            if 块 is not None:
                self.编辑器.切换折叠(块)
                return
        super().mousePressEvent(事件)

    def mouseMoveEvent(self, 事件):
        块 = self.折叠三角处(事件.position().toPoint())
        新 = 块.blockNumber() if 块 is not None else -1
        if 新 != self._悬停块:
            self._悬停块 = 新
            self.update()
        self.setCursor(Qt.PointingHandCursor if 块 is not None else Qt.ArrowCursor)
        super().mouseMoveEvent(事件)

    def leaveEvent(self, 事件):
        if self._悬停块 != -1:
            self._悬停块 = -1
            self.update()
        super().leaveEvent(事件)


# ---------------------------------------------------------------------------
# 编辑器
# ---------------------------------------------------------------------------


class 编辑器(QPlainTextEdit):
    """PyCharm 风格代码编辑器，带行号、当前行、缩进参考线、代码折叠。"""

    光标移动 = Signal()

    def __init__(self, 主窗, 父=None):
        super().__init__(父)
        self.主窗 = 主窗
        self.文件路径 = None
        self.已改 = False
        # 制表宽从主窗读：设置里改缩进要作用于**已打开**的文档，
        # 以前写死 4，只有新建的文档才拿到新值。
        self.制表宽 = int(getattr(主窗, "制表宽", 4))
        # 输入法组字状态（由 inputMethodEvent 维护）
        self._组字中 = False
        # 当前折起来的块数。0 表示没有折叠 —— 文本变化时据此跳过全文重算。
        self._折叠数 = 0
        # 最近一次文本改动落在哪个字符位置（-1 = 自上次建缓存以来没改过）。
        # 折叠区缓存靠它判断缓存是否还成立，见 折叠区 / _缓存边界。
        self._编辑位置 = -1

        self.设置字体()

        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setTabChangesFocus(False)

        self.行号 = 行号区(self)
        self.块数变化 = self.blockCountChanged
        self.块数变化.connect(self._更新行号宽)
        self.updateRequest.connect(self._更新行号区)
        self.cursorPositionChanged.connect(self._当前行变化)
        self.textChanged.connect(self._文本变化)

        self.高亮 = 高亮器(self.document(), 主窗)

        # 界面刷新去抖器：文本/光标变化都攒到这里，避免在输入过程中
        # 同步改窗口标题和状态栏（那会引起重排重绘并丢字）
        self._界面刷新任务 = QTimer(self)
        self._界面刷新任务.setSingleShot(True)
        self._界面刷新任务.setInterval(30)
        self._界面刷新任务.timeout.connect(self._补记已改)
        self.cursorPositionChanged.connect(self._排队刷新界面)

        # 尊重主窗口的「显示行号」开关
        self._行号隐藏 = not getattr(主窗, "显示行号", True)
        self._缩进线开 = bool(getattr(主窗, "显示缩进线", True))
        if self._行号隐藏:
            self.行号.setVisible(False)
        self._更新行号宽()
        self._当前行变化()

    def _排队刷新界面(self, *_):
        """光标动了也走同一个去抖器（不直接刷 UI）。"""
        任务 = getattr(self, "_界面刷新任务", None)
        if 任务 is not None:
            任务.start(30)

    # —— 字体与主题 ——

    def 设置字体(self, 字号=None):
        self.字号 = 字号 or getattr(self.主窗, "字号", 12)
        字体 = QFont(挑等宽字体(), self.字号)
        字体.setStyleHint(QFont.Monospace)
        self.setFont(字体)
        if hasattr(self, "行号"):
            self.行号.setFont(字体)
            # 注意：QSS 里 QPlainTextEdit/#gutter 也写了 font-size，
            # 其优先级高于 setFont()，所以 setFont 之后真正的字体
            # 由样式表决定。制表宽度必须按「实际生效的字体」算，
            # 否则字号一大，tab 位置就和显示对不上。
            实际 = self.fontMetrics()
            self.setTabStopDistance(
                实际.horizontalAdvance(" ") * self.制表宽
            )
            # 字号变了，行号栏需要的宽度也变了，必须重算
            self._更新行号宽()
            self.行号.update()
        else:
            self.setTabStopDistance(
                QFontMetrics(字体).horizontalAdvance(" ") * self.制表宽
            )

    def 换主题(self):
        self.高亮.重建()
        self.高亮.rehighlight()
        self.行号.update()
        # 应用样式表会重置 viewportMargins，必须重设，否则文字会贴到最左边
        self.重设行号边距()
        self._当前行变化()

    def 应用设置(self):
        """把主窗上的所有界面设置一次性同步到这个编辑器。

        设置窗口每改一项就调它 —— 这样「行号/缩进线/缩进宽/字号/高亮」
        全都当场生效，不用关掉软件重开。
        """
        主窗 = self.主窗
        self.设置字体(getattr(主窗, "字号", None))
        self.制表宽 = max(1, int(getattr(主窗, "制表宽", self.制表宽)))
        self.setTabStopDistance(
            QFontMetrics(self.font()).horizontalAdvance(" ") * self.制表宽
        )
        self.设行号(getattr(主窗, "显示行号", True))
        self.设自动高亮(getattr(主窗, "自动高亮", True))
        # 缩进线要走 设缩进线()，它除了改属性还会调 viewport().update()。
        # 只改属性的话，勾选框切换后要等下一次重绘才看得出变化。
        self.设缩进线(getattr(主窗, "显示缩进线", True))
        self.update()

    # —— 设置项（改完立刻生效，不用重启）——

    def 设行号(self, 显示):
        """切换行号栏。设置窗口勾一下就调它，不用重开程序。"""
        self._行号隐藏 = not 显示
        self.行号.setVisible(bool(显示))
        self._更新行号宽()
        self.重设行号边距()

    def 设制表宽(self, 宽):
        self.制表宽 = max(1, int(宽))
        self.设置字体(self.字号)
        self._当前行变化()

    def 设缩进线(self, 显示):
        """切换缩进参考线。重绘即可 —— 是否画线由 _缩进线开 决定。"""
        self._缩进线开 = bool(显示)
        self.viewport().update()

    def 设自动高亮(self, 开):
        """开关语法高亮。

        不能只是「以后不再重建规则」——QSyntaxHighlighter 一旦挂上就一直
        生效，用户勾掉「输入时自动语法高亮」后文字依然彩色，看起来像
        设置没生效。这里让高亮器自己在 highlightBlock 里直接返回，
        再 rehighlight 一次把已染上的颜色洗掉。
        """
        self.高亮.开 = bool(开)
        self.高亮.rehighlight()

    # —— 代码折叠 ——
    #
    # 折叠什么：以冒号结尾、且**下一行缩进更深**的行。
    #   核若 x：            ← 可折叠
    #       核说(x)         ← 被折起来的部分
    #   核说(1)             ← 缩进回到同级，折叠到此为止
    # 核语言里块的开头必然是冒号（半角全角都认），所以判定很直接，
    # 不需要真的做语法分析。

    @staticmethod
    def 缩进数(文本):
        """这一行开头的空白宽度（制表符按 1 个字符算，不做制表宽换算）。"""
        剥 = 文本.lstrip(" \t\u3000")
        return len(文本) - len(剥)

    @staticmethod
    def 是块开头(文本):
        """这一行是不是一个块的开头（以冒号结尾）。

        判定口径统一走 核.扫描行：先切掉行尾注释，再看最后一个有效字符
        是不是冒号。之前是 剥.find("核核") 直接切 —— 既不认「核核紧贴」
        的边界规则，也会把字符串里的「核核」当注释开头，和翻译器说法不同；
        而且字符串里的冒号（核说("a:")）会被误判成块开头。
        """
        串区, 注释起, _ = 核.扫描行(文本)
        剥 = 文本[:注释起] if 注释起 >= 0 else 文本
        剥 = 剥.rstrip()
        if not 剥:
            return False
        位 = len(剥) - 1
        if any(起 <= 位 < 止 for 起, 止 in 串区):
            return False
        return 剥.endswith("：") or 剥.endswith(":")

    def 折叠区(self, 块):
        """返回该块能折起来的最后一行号（含），不能折则 None。

        结果缓存在块上（见 折叠数据）。缓存只在「本行之后、界块之前」
        被改过时才作废 —— 区域边界只取决于这一段的缩进。
        """
        if 块 is None or not 块.isValid():
            return None
        文本 = 块.text()
        if not self.是块开头(文本):
            return None
        数据 = self._数据(块)
        命中 = self._缓存边界(块, 数据, 文本)
        if 命中 is not None:
            return 命中
        止, 界块 = self._算折叠区(块, 文本)
        if 数据 is not None:
            文档 = self.document()
            数据.区头文本 = 文本
            数据.区止块 = 文档.findBlockByNumber(止) if 止 is not None else None
            数据.区界块 = 界块
        return 止

    def _缓存边界(self, 块, 数据, 文本):
        """缓存仍成立时返回缓存的止行号；不成立返回 None。"""
        if 数据 is None or 数据.区头文本 != 文本 or 数据.区止块 is None:
            return None
        if not 数据.区止块.isValid():
            return None
        编辑 = getattr(self, "_编辑位置", -1)
        if 编辑 < 块.position():
            # 改动在本行之前：本行自己的区域没有任何理由改变
            return 数据.区止块.blockNumber()
        界块 = 数据.区界块
        if 界块 is None:
            # 区域一直延伸到文末，只要本行之后被改过就不敢复用
            return None
        if not 界块.isValid():
            return None
        if 编辑 < 界块.position():
            # 改动落在区域内、尾随空行里，或正是让区域停下的那一行上
            return None
        return 数据.区止块.blockNumber()

    def _算折叠区(self, 块, 文本):
        """真正向下扫一遍，返回 (止行号或 None, 界块或 None)。"""
        缩进 = self.缩进数(文本)
        起 = 块.blockNumber() + 1
        止 = -1
        当前 = self.document().findBlockByNumber(起)
        while 当前.isValid():
            行 = 当前.text()
            if not 行.strip():
                # 空行先跳过，但只有它后面还有更深缩进的行时才纳入范围
                下一 = 当前.next()
                while 下一.isValid() and not 下一.text().strip():
                    下一 = 下一.next()
                if 下一.isValid() and self.缩进数(下一.text()) > 缩进:
                    止 = 当前.blockNumber()
                    当前 = 当前.next()
                    continue
                return (止 if 止 >= 起 else None), (下一 if 下一.isValid() else None)
            if self.缩进数(行) <= 缩进:
                return (止 if 止 >= 起 else None), 当前
            止 = 当前.blockNumber()
            当前 = 当前.next()
        return (止 if 止 >= 起 else None), None

    def 可折叠(self, 块):
        return self.折叠区(块) is not None

    def _数据(self, 块, 需要时新建=False):
        """取块上的折叠数据（可选地在没有时创建）。"""
        if 块 is None or not 块.isValid():
            return None
        数据 = 块.userData()
        if 数据 is None and 需要时新建:
            数据 = 折叠数据()
            块.setUserData(数据)
        return 数据

    def 已折叠(self, 块):
        数据 = self._数据(块)
        return bool(数据 is not None and 数据.折叠)

    def 切换折叠(self, 块):
        """展开/折起这一块。"""
        if not self.可折叠(块):
            return
        if self.已折叠(块):
            self._数据(块).折叠 = False
        else:
            self._数据(块, 需要时新建=True).折叠 = True
            # 折叠前先把光标移出这一块，否则光标会停在看不见的行上
            self.移出折叠区(块)
        self.应用折叠()
        self.行号.update()
        self.viewport().update()

    def 移出折叠区(self, 开头块):
        """若光标正落在即将折起的范围内，把它挪到块开头那一行。"""
        止 = self.折叠区(开头块)
        if 止 is None:
            return
        游 = self.textCursor()
        行 = 游.blockNumber()
        if 开头块.blockNumber() < 行 <= 止:
            新 = QTextCursor(开头块)
            新.movePosition(QTextCursor.EndOfBlock)
            self.setTextCursor(新)

    def 全部展开(self):
        """把所有折叠都展开。"""
        块 = self.document().firstBlock()
        改了 = False
        while 块.isValid():
            数据 = 块.userData()
            if 数据 is not None and getattr(数据, "折叠", False):
                数据.折叠 = False
                改了 = True
            块 = 块.next()
        if 改了:
            self.应用折叠()
            self.行号.update()
            self.viewport().update()
        else:
            self._折叠数 = 0

    def 全部折叠(self):
        """把所有可折叠的块都折起来。"""
        块 = self.document().firstBlock()
        有 = False
        while 块.isValid():
            if self.可折叠(块):
                self._数据(块, 需要时新建=True).折叠 = True
                有 = True
            块 = 块.next()
        if 有:
            # 光标可能落在被折起的行上，先挪到文末（可见）
            游 = self.textCursor()
            游.movePosition(QTextCursor.End)
            self.setTextCursor(游)
            self.应用折叠()
            self.行号.update()
            self.viewport().update()

    def 应用折叠(self):
        """按每块的折叠标记重新设置可见性。

        先假定全部可见再逐块隐藏：折叠区域在编辑后会变（缩进改了、
        冒号删了），只往里加不往外放的话，展开之后那些行仍然是隐藏的。

        **性能**：折叠范围缓存在块上（见 折叠区），所以本函数的成本就剩
        一次遍历。遍历本身没法省（每一块的可见性都要确认），但
        `_文档重排`（markContentsDirty 全文 + 重排）只在可见性**真的变了**
        时才做 —— 以前每敲一键都无条件要求整篇重排，这是最贵的一环。
        注意不能用 QTextBlock.isVisible() 判断「当前是什么状态」：
        控件自身隐藏时它会一律返回 False，拿它比对会把每次都判成「变了」，
        反而让所有块被重新设一遍；所以自己留一份上次的结果（_可见表）。
        """
        文档 = self.document()
        块 = 文档.firstBlock()
        折叠中 = 0          # 还需要隐藏到第几块
        个数 = 0
        新表 = []
        while 块.isValid():
            号 = 块.blockNumber()
            if 折叠中 and 号 > 折叠中:
                折叠中 = 0
            要藏 = bool(折叠中)
            if not 要藏:
                数据 = 块.userData()
                if 数据 is not None and getattr(数据, "折叠", False):
                    止 = self.折叠区(块)
                    if 止 is not None:
                        折叠中 = 止
                        个数 += 1
                    else:
                        # 已经不是一个块开头了（比如冒号被删了），清掉标记
                        数据.折叠 = False
            可见 = not 要藏
            新表.append(可见)
            块.setVisible(可见)
            块 = 块.next()
        self._折叠数 = 个数
        if 新表 != getattr(self, "_可见表", None):
            self._可见表 = 新表
            self._文档重排()

    def _文档重排(self):
        """让 Qt 按新的可见性重新排版。

        setVisible 只改标记，不会自动重算文档高度 —— 不通知的话
        被折起来的行仍然占着位置（或者反过来，展开后不占位）。
        """
        文档 = self.document()
        try:
            文档.markContentsDirty(0, 文档.characterCount())
        except (AttributeError, TypeError):
            pass
        框 = self.viewport()
        框.update()
        self._更新行号宽()

    def _块在y(self, y):
        """行号栏里这个 y 坐标对应哪个块（用于命中测试）。"""
        编辑器 = self
        块 = 编辑器.firstVisibleBlock()
        偏移 = 编辑器.viewport().y() - self.y()
        顶 = (
            int(
                编辑器.blockBoundingGeometry(块)
                .translated(编辑器.contentOffset())
                .top()
            )
            + 偏移
        )
        安全 = 0
        while 块.isValid() and 安全 < 20000:
            高 = int(编辑器.blockBoundingRect(块).height())
            下 = 顶 + max(高, 0)
            if 顶 <= y < 下:
                return 块
            # 被折起来的块高度为 0，跳过时不算命中也别死循环
            顶 = 下
            块 = 块.next()
            安全 += 1
        return None

    # —— 行号 ——

    def _更新行号宽(self, _=None):
        # 行数变多时把行号栏加宽，避免正文被挤在行号下面
        try:
            self.行号.按行号调整宽度(self.blockCount())
        except (AttributeError, RuntimeError):
            pass
        # 用「是否被隐藏」判断，不能用 isVisible()：
        # 编辑器还没显示到屏幕上时 isVisible() 是 False，会算出左边距 0，
        # 结果正文贴着最左边画、和行号栏重叠（看起来就是「行首被吞」）。
        左边距 = 0 if getattr(self, "_行号隐藏", False) else self.行号.宽度
        self.setViewportMargins(左边距, 0, 0, 0)

    def 重设行号边距(self):
        """样式表一改，Qt 会把 viewportMargins 重置掉，必须重新设一次。

        现象：换主题后文字突然贴到最左边、和行号栏叠在一起，
        看起来像每行开头被切掉了几个字（用户报的「每行吞字」）。
        """
        self._更新行号宽()
        try:
            区 = self.contentsRect()
            self.行号.setGeometry(
                QRect(区.left(), 区.top(), self.行号.宽度, 区.height())
            )
        except (AttributeError, RuntimeError):
            pass

    def _更新行号区(self, 矩形, 滚动):
        if 滚动:
            self.行号.scroll(0, 滚动)
        else:
            self.行号.update(0, 矩形.y(), self.行号.width(), 矩形.height())

    def resizeEvent(self, 事件):
        super().resizeEvent(事件)
        区 = self.contentsRect()
        self.行号.setGeometry(QRect(区.left(), 区.top(), self.行号.宽度, 区.height()))

    def 当前行号(self):
        return self.textCursor().blockNumber()

    # —— 当前行高亮 + 缩进参考线 ——

    def _当前行变化(self):
        色 = self.主窗.主题
        选区 = QTextEdit.ExtraSelection()
        选区.format.setBackground(QColor(色["当前行"]))
        选区.format.setProperty(0x100000, True)  # FullWidthSelection
        选区.cursor = self.textCursor()
        选区.cursor.clearSelection()
        self.setExtraSelections([选区])
        # 安全网：光标万一落到被折起来的行上（Ctrl+End、查找定位、
        # 撤销都可能），就把那一块展开 —— 绝不能让人在看不见的行上打字。
        self._展开光标处的折叠()
        self.光标移动.emit()

    def _展开光标处的折叠(self):
        if not getattr(self, "_折叠数", 0):
            return
        块 = self.textCursor().block()
        if 块.isValid() and not 块.isVisible():
            self._展开含此块的折叠(块.blockNumber())

    def _展开含此块的折叠(self, 行号):
        """把「覆盖了这一行」的那个折叠展开。"""
        块 = self.document().firstBlock()
        while 块.isValid():
            数据 = 块.userData()
            if (
                数据 is not None
                and getattr(数据, "折叠", False)
                and 块.blockNumber() < 行号
            ):
                止 = self.折叠区(块)
                if 止 is not None and 行号 <= 止:
                    数据.折叠 = False
                    self.应用折叠()
                    self.行号.update()
                    return
            块 = 块.next()

    def _文本变化(self):
        """文本变了。这里只做最轻的记账，重的 UI 更新一律延后。

        教训：以前在这里同步调 `更新状态栏()` 和 `_刷新标题()`，
        它们会改状态栏文字和窗口标题，引起重排重绘并重入事件循环；
        连续快速输入（尤其配合输入法）时会丢字，用户看到的就是「吞字」。
        现在改成去抖：无论触发多少次，只在一个事件循环之后做一次。
        """
        if getattr(self, "_载入中", False):
            return
        # 记下这次改动落在哪儿：折叠区缓存靠它判断「还管不管用」。
        # 拿不到就别用缓存（_缓存边界 会一律判失效），宁慢不错。
        游 = self.textCursor()
        self._编辑位置 = min(游.position(), 游.anchor())
        # 有折叠时才重算可见性：折叠标记挂在块上，
        # 编辑之后块的相对关系会变（缩进改了、冒号删了），
        # 必须重新算一遍「哪些块该藏起来」。没有折叠就完全跳过 ——
        # 否则每敲一个字都要走一遍全文。
        #
        # 这里刻意**不做去抖**：折叠范围已经缓存在块上，落在改动之外
        # 的区域不会重算，实测 500/2000/8000 行分别是 0.4/2.4/7.1ms，
        # 直接同步算完全可以接受；去抖反而会让「删掉冒号后区域该展开」
        # 这类变化延迟一拍才生效。
        if getattr(self, "_折叠数", 0):
            self.应用折叠()
            self.行号.update()
        if not self.已改:
            self.已改 = True
            self.主窗.刷新标签(self)
        # 去抖调度（_排重界面刷新 由编辑器构造时创建）
        任务 = getattr(self, "_界面刷新任务", None)
        if 任务 is not None:
            任务.start(30)

    def _补记已改(self):
        """延后执行的界面刷新：标题栏 ● 与状态栏行列。

        关键：输入法正在组字时绝不刷窗口标题。
        Windows 上 `setWindowTitle` 会取消 IME 组字 —— 用户飞快打拼音、
        组字还没上屏时，定时器一改标题，正在输入的组字就被取消了，
        表现就是「每行都会吞字」。组字中就把这次刷新推迟再来。
        """
        if getattr(self, "_载入中", False):
            return
        if self._输入法组字中():
            任务 = getattr(self, "_界面刷新任务", None)
            if 任务 is not None:
                任务.start(120)
            return
        if self.主窗.当前 is self:
            self.主窗._刷新标题()
        self.主窗.更新状态栏()

    def paintEvent(self, 事件):
        super().paintEvent(事件)
        # 用本地缓存，不直接读主窗：设置对话框里切线时主窗可能还没同步，
        # 而且每次重绘都读一次属性、勾选框关掉后要等下一帧才生效。
        if getattr(self, "_缩进线开", getattr(self.主窗, "显示缩进线", True)):
            self._画缩进线()

    def _画缩进线(self):
        """按行画缩进参考线。

        PyCharm 的做法：只在这一行**有缩进**时，于对应缩进层级画一小段竖线；
        空行、无缩进的行都不画。

        只画「外层」层级，不画这一行自己那一级：第 8 行缩进 4 个空格
        （1 级），线画在 x=16，而正文从 x=19 开始 —— 两者只差 3px，
        看起来就像「数字们」前面多了一个竖线字符（用户报过像多出个符号）。
        改成 range(1, 级) 之后，1 级缩进的行不再画线，2 级才在 1 级处画一条，
        和 PyCharm / VS Code 一致。
        """
        色 = self.主窗.主题
        绘 = QPainter(self.viewport())
        绘.setPen(QPen(QColor(色["缩进线"]), 1))
        字宽 = QFontMetrics(self.font()).horizontalAdvance(" ")
        宽 = 字宽 * self.制表宽
        if 宽 <= 0:
            return
        偏移 = int(self.contentOffset().x())
        可见底 = self.viewport().height()

        块 = self.firstVisibleBlock()
        while 块.isValid():
            矩形 = self.blockBoundingGeometry(块).translated(self.contentOffset())
            顶 = int(矩形.top())
            if 顶 > 可见底:
                break
            高 = int(矩形.height())
            if 顶 + 高 >= 0:
                文 = 块.text()
                if 文.strip():
                    # 这行有几级缩进，就在它**外面**的层级画线
                    前导 = len(文) - len(文.lstrip(" \t"))
                    级 = 前导 // self.制表宽
                    for i in range(1, 级):
                        x = 偏移 + 宽 * i
                        if x >= self.viewport().width():
                            break
                        绘.drawLine(x, 顶, x, 顶 + 高)
            块 = 块.next()

    # —— 键盘行为 ——

    def inputMethodEvent(self, 事件):
        """跟踪输入法组字状态。

        之前用 `QGuiApplication.inputMethod().isVisible()` 判断，但那个接口
        在 Windows 上并不可靠（实测始终 False），导致「输入法组字中要放行」
        的守卫从未生效：用户打拼音时按到 `'` `"` 被自动配对截走，
        输入法收不到按键，正在组的那段就没了 —— 就是「吞字」。
        这里自己记账：有 preedit 就是组字中，提交或清空就结束。
        """
        预编辑 = 事件.preeditString() if 事件 is not None else ""
        self._组字中 = bool(预编辑)
        super().inputMethodEvent(事件)

    def _输入法组字中(self):
        """是否正在用输入法组字（自己记账，不依赖平台接口）。"""
        return bool(getattr(self, "_组字中", False))

    # 自动配对要放行的修饰键。Shift 必须放行：
    # 真实键盘上 ( ) { } " 全都要按住 Shift 才打得出来，
    # 事件.modifiers() 必然带着 ShiftModifier，若一律不给配对
    # 这几个符号的配对就整个失效（0.0.8 使用 301a395 引入的回归）。
    # Ctrl / Alt / Meta 组合仍然要让路给快捷键。
    #
    # 这里特意**用整数做位运算**，不用 `事件.modifiers() & ~Qt.ShiftModifier`：
    # PySide6 的 Qt.KeyboardModifier 只声明了老的那几位
    # （位掩码 0x1FFFFFF），而 ControlModifier = 0x4000000 在掩码之外，
    # 于是 `~Qt.ShiftModifier` 取不到 Ctrl 那一位 —— 实测
    # Ctrl+( 仍然会被自动配对，正是要防的情况。转成 int 就没这问题。
    配对放行修饰 = int(Qt.ShiftModifier.value)

    def _无配对外修饰(self, 事件: QKeyEvent):
        """除了 Shift 之外没按别的修饰键 —— 才由本类处理这次按键。"""
        return not (int(事件.modifiers().value) & ~self.配对放行修饰)

    配对表 = {
        "(": ")", "[": "]", "{": "}", "'": "'", '"': '"',
        "（": "）", "【": "】", "｛": "｝",
    }

    def keyPressEvent(self, 事件: QKeyEvent):
        键 = 事件.key()
        文本 = 事件.text()

        if 键 in (Qt.Key_Return, Qt.Key_Enter):
            self._自动缩进(事件)
            return
        if 键 == Qt.Key_Tab:
            self._缩进选中行(1)
            return
        if 键 == Qt.Key_Backtab:
            self._缩进选中行(-1)
            return
        # 自动配对括号与引号。
        # 中文输入法正在组字时一律让路：IME 用 ' 和 " 触发中文标点，
        # 若这里抢先生成一对英文引号并 return，输入法就收不到这次按键，
        # 用户会觉得「标点被吞了、打不出来」。
        组字中 = self._输入法组字中()
        # 「右邻已经是配对的另一半」时直接跳过，不再插一对。
        #
        # 这一步必须排在自动配对**之前**，而且对引号同样适用。
        # 以前引号不在这里处理：引号既是配对表的键又是值，
        # 所以按 '"' 时先命中上面的自动配对分支、插出一对 ""，
        # 用户再按 '"' 收尾时又插一对 —— 打 核说("中文") 出来是
        # 核说("中文")"")，凭空多三个字符。
        if 文本 and 文本 in self.配对表 and not 组字中 and self._无配对外修饰(事件):
            游 = self.textCursor()
            if not 游.hasSelection():
                行文 = 游.block().text()
                位 = 游.positionInBlock()
                if 行文[位:位 + 1] == self.配对表[文本]:
                    # 右边就是配对的那一半 —— 光标移过去即可
                    游.movePosition(QTextCursor.Right)
                    self.setTextCursor(游)
                    return
        if 文本 in self.配对表 and self._无配对外修饰(事件) and not 组字中:
            self._自动配对(文本, self.配对表[文本])
            return
        if 组字中 and 文本 in self.配对表:
            # 组字期间这类按键交给输入法决定（它会把 ' 变成 ’ 之类），
            # 自己不能再插一个字符，否则上屏后多出个引号。
            事件.accept()
            return
        # 输入右括号时，若紧邻的正是它，直接跳过（不重复插入）
        if 文本 and 文本 in self.配对表.values() and not 组字中 and self._无配对外修饰(事件):
            游 = self.textCursor()
            if not 游.hasSelection() and 游.block().text()[游.positionInBlock():游.positionInBlock() + 1] == 文本:
                游.movePosition(QTextCursor.Right)
                self.setTextCursor(游)
                return
        # 按退格删除成对符号时，把另一半也删掉
        if 键 == Qt.Key_Backspace:
            游 = self.textCursor()
            if not 游.hasSelection():
                行 = 游.block().text()
                列 = 游.positionInBlock()
                if 列 > 0 and 列 < len(行):
                    左 = 行[列 - 1]
                    右 = 行[列]
                    if self.配对表.get(左) == 右:
                        # 用文档游标删掉这两个字符，位置从「列-1」到「列+1」
                        起 = 游.position() - 1
                        止 = 游.position() + 1
                        删 = QTextCursor(self.document())
                        删.setPosition(起)
                        删.setPosition(止, QTextCursor.KeepAnchor)
                        删.removeSelectedText()
                        return
        super().keyPressEvent(事件)

    def wheelEvent(self, 事件):
        """Ctrl+滚轮 缩放字号（编辑器通用操作）。"""
        if 事件.modifiers() & Qt.ControlModifier:
            差 = 1 if 事件.angleDelta().y() > 0 else -1
            self.主窗.改字号(差)
            事件.accept()
            return
        super().wheelEvent(事件)

    def _自动配对(self, 左, 右):
        """插入一对括号；若选中了文字，则把选区包起来。

        包住选区的做法：先在选区起止各插一个符号（从后往前插，
        这样前面的偏移不受影响），再恢复原来的选区。
        """
        游 = self.textCursor()
        if 游.hasSelection():
            起 = 游.selectionStart()
            止 = 游.selectionEnd()
            文档 = self.document()
            # 先插右边，再插左边，位置才不会互相影响
            尾 = QTextCursor(文档)
            尾.setPosition(止)
            尾.insertText(右)
            头 = QTextCursor(文档)
            头.setPosition(起)
            头.insertText(左)
            # 恢复选中中间那段
            新 = QTextCursor(文档)
            新.setPosition(起 + 1)
            新.setPosition(止 + 1, QTextCursor.KeepAnchor)
            self.setTextCursor(新)
            return
        游.insertText(左 + 右)
        游.movePosition(QTextCursor.Left)
        self.setTextCursor(游)

    def _自动缩进(self, 事件):
        """回车时保持缩进；若上一行以冒号结尾再缩进一级。

        实测 QPlainTextEdit 的原生回车**不会**继承上一行缩进（第 2 行是空的），
        所以要自己补完整的缩进量，而不是只补差额。

        判定块开头用 是块开头 —— 与折叠用的是同一个方法。
        以前这里自己写 rstrip().endswith(":")，不剥行尾注释，
        于是「核若 对： 核核 说明」后回车不缩进，而同一行却能折叠：
        同一个「块开头」两处口径不一致，用户看到的是莫名其妙的行为。
        """
        光标 = self.textCursor()
        行文 = 光标.block().text()[: 光标.positionInBlock()]
        缩进 = len(行文) - len(行文.lstrip(" \t\u3000"))
        额外 = self.制表宽 if self.是块开头(行文) else 0
        空格 = " " * (缩进 + 额外)
        super().keyPressEvent(事件)
        if 空格:
            游 = self.textCursor()
            游.insertText(空格)
            self.setTextCursor(游)

    def _缩进选中行(self, 方向):
        光标 = self.textCursor()
        起 = self.document().findBlock(光标.selectionStart()).blockNumber()
        止 = self.document().findBlock(光标.selectionEnd()).blockNumber()
        游标 = self.textCursor()
        游标.beginEditBlock()
        空格 = " " * self.制表宽
        for 行 in range(起, 止 + 1):
            块 = self.document().findBlockByNumber(行)
            游 = QTextCursor(块)
            if 方向 > 0:
                游.insertText(空格)
                continue
            文 = 块.text()
            if 文.startswith(空格):
                游.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, self.制表宽)
                游.removeSelectedText()
            elif 文.startswith("\t"):
                游.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, 1)
                游.removeSelectedText()
        游标.endEditBlock()

    # —— 注释切换 ——

    #: 认得的注释前缀。核语言用「核核 」，英文「#」也照样能用（见 说明.md），
    #: 所以切换注释两种都要认 —— 以前只认「核核 」，
    #: 英文 # 注释行永远被当成「没注释」，在混排文件里行为不一致。
    注释前缀 = ("核核 ", "#", "# ")

    @classmethod
    def _取注释前缀(cls, 文):
        """这一行的注释前缀（去掉缩进后看）；不是注释行则返回 None。

        「核核」后必须不是标识符字符 —— 和 核.py 翻译器的判定一致，
        否则「核核紧贴」会被误当成注释。
        """
        剥 = 文.lstrip()
        if 剥.startswith("核核"):
            后面 = 剥[2:]
            if not 后面 or not (
                后面[0] == "_"
                or 后面[0].isalnum()
                or (ord(后面[0]) > 127 and 后面[0].isidentifier())
            ):
                return "核核"
        if 剥.startswith("#"):
            return "#"
        return None

    def 切换注释(self):
        """给选中的行加/去注释。

        两条硬规矩 —— 破坏代码的两条路：

        1. **字符串里的内容不能动**。多行三引号串的中间几行在语法上是
           字符串的一部分，在那里插一个「核核 」会直接改掉程序的输出。
           实测：
               核说(\"\"\"第一行
               # 井号行
               第三行\"\"\")
           切一次就变成「核核 第三行\"\"\"」—— 程序输出当场变了。
           所以要先问内核：这个位置是不是在字符串里。

        2. **已经是注释的行不要套第二层**。「核核 已有」再加一次会变成
           「核核 核核 已有」，之后再也去不掉。

        注释前缀统一用「核核 」（核语言自己的写法），不再按行混用 # ——
        同一个文件里有的行是 #、有的行是 核核，来回切注释就会漂移。
        """
        光标 = self.textCursor()
        起 = self.document().findBlock(光标.selectionStart()).blockNumber()
        止 = self.document().findBlock(光标.selectionEnd()).blockNumber()
        块们 = [self.document().findBlockByNumber(i) for i in range(起, 止 + 1)]
        有内容 = [b for b in 块们 if b.text().strip()]
        if not 有内容:
            return
        # 先算每一行「哪些字符在字符串里」。
        # 多行三引号串会跨块，所以要按块序号记住「上一块结束时字符串还没闭合」。
        串行 = self._标出字符串的块(块们)
        前缀们 = [
            None if 串行.get(b.blockNumber()) else self._取注释前缀(b.text())
            for b in 有内容
        ]
        # 全注释 = 每一行都**已经是注释行**。
        # 以前只判「全是同一种前缀」，于是
        #   核说(1)          ← 代码
        #   核核 已有         ← 已经是注释
        # 这种混合块会被当成「要加注释」，给已经有注释的那行**再加一层** ——
        # 变成「核核 核核 已有」，第二次切换又只去掉一个，注释再也去不掉。
        全注释 = all(p is not None for p in 前缀们)
        游标 = self.textCursor()
        游标.beginEditBlock()
        for 块 in 块们:
            文 = 块.text()
            if not 文.strip():
                continue
            编号 = 块.blockNumber()
            if 编号 in 串行:
                # 这一行在字符串里：一个字符都不能动
                continue
            缩进 = len(文) - len(文.lstrip())
            体 = 文[缩进:]
            游 = QTextCursor(块)
            if 全注释:
                # 去掉注释前缀。原来是「核核 abc」就只去掉「核核 」，
                # 原来是「# abc」就只去掉「#」和它后面那个空格。
                去掉 = 体
                if 去掉.startswith("核核"):
                    去掉 = 去掉[2:]
                    if 去掉.startswith(" "):
                        去掉 = 去掉[1:]
                elif 去掉.startswith("#"):
                    去掉 = 去掉[1:]
                    if 去掉.startswith(" "):
                        去掉 = 去掉[1:]
                新文 = 文[:缩进] + 去掉
                游.movePosition(QTextCursor.StartOfBlock)
                游.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
                游.insertText(新文)
            else:
                # 已经是注释的行不动 —— 再套一层就再也去不掉了。
                if self._取注释前缀(体) is not None:
                    continue
                游.movePosition(QTextCursor.StartOfBlock)
                游.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor, 缩进)
                游.insertText("核核 ")
        游标.endEditBlock()

    def _标出字符串的块(self, 块们):
        """返回 {块号: 该块是否在字符串里}。

        用内核自己的扫描器（核.扫描行），跨块的三引号串靠块状态接续 ——
        与语法高亮、转译器用的是同一套判定。
        """
        结果 = {}
        起始 = None
        核 = self.主窗.内核
        for 块 in 块们:
            文本 = 块.text()
            串区, 注释起, 未闭合 = 核.扫描行(文本, 起始)
            if 未闭合:
                起始 = 未闭合
                结果[块.blockNumber()] = True
                continue
            起始 = None
            if 串区:
                # 这一行有字符串，但只有**字符串之外**的部分才能加注释。
                # 单行字符串独占一行时（整行就是字符串）也不能动。
                体 = 文本.lstrip()
                if 注释起 >= 0:
                    # 有注释：注释之前有字符串吗？
                    前面的串 = [区 for 区 in 串区 if 区[1] <= 注释起]
                else:
                    前面的串 = 串区
                if 前面的串 and not 文本[:前面的串[0][0]].strip():
                    # 整行从字符串开始 —— 加注释会把字符串封在注释里
                    结果[块.blockNumber()] = True
                elif 前面的串:
                    # 字符串前面有代码（如 核说("...")）：只能动字符串**之后**的部分，
                    # 太细了，索性整行不动 —— 宁可少注释一行，也不能改坏代码。
                    结果[块.blockNumber()] = True
        return 结果

    # —— 查找 ——

    def 查找下一个(self, 词, 区分大小写=False):
        if not 词:
            return False
        旗 = QTextDocument.FindFlag(0)
        if 区分大小写:
            旗 = QTextDocument.FindCaseSensitively
        找到 = self.find(词, 旗)
        if not 找到:
            游 = self.textCursor()
            游.movePosition(QTextCursor.Start)
            self.setTextCursor(游)
            找到 = self.find(词, 旗)
        return bool(找到)

    def 替换当前(self, 查找词, 替换词, 区分大小写=False):
        """替换当前选中的匹配项（没有选中就先找一个）。

        区分大小写必须一路传下来：查找用精确旗标定位、替换却按
        不敏感口径认选中项，两边口径不一致，替换会换掉用户没看到的词。
        """
        游 = self.textCursor()
        选中 = 游.selectedText()
        符合 = (选中 == 查找词) if 区分大小写 else (选中.casefold() == 查找词.casefold())
        if not 游.hasSelection() or not 符合:
            if not self.查找下一个(查找词, 区分大小写):
                return False
            游 = self.textCursor()
        游.insertText(替换词)
        self.setTextCursor(游)
        return True

    def 全部替换(self, 查找词, 替换词, 区分大小写=False):
        """替换全部匹配项，返回替换次数。"""
        if not 查找词:
            return 0
        旗 = QTextDocument.FindFlag(0)
        if 区分大小写:
            旗 = QTextDocument.FindCaseSensitively
        次数 = 0
        游 = QTextCursor(self.document())
        游.beginEditBlock()
        游.movePosition(QTextCursor.Start)
        while True:
            self.setTextCursor(游)
            if not self.find(查找词, 旗):
                break
            游 = self.textCursor()
            游.insertText(替换词)
            次数 += 1
        游.endEditBlock()
        self.setTextCursor(QTextCursor(self.document()))
        return 次数

    def 跳到行(self, 行号):
        """跳到指定行（1 起）。"""
        块 = self.document().findBlockByNumber(max(0, int(行号) - 1))
        if not 块.isValid():
            return False
        游 = QTextCursor(块)
        self.setTextCursor(游)
        self.centerCursor()
        self.setFocus()
        return True

    def 当前行列(self):
        """返回 (行, 列)，都从 1 起。"""
        游 = self.textCursor()
        return 游.blockNumber() + 1, 游.positionInBlock() + 1

    # —— 文件 ——

    def 取文本(self):
        return self.toPlainText()

    def 置文本(self, 文本, 标记已改=False):
        """替换全部文本。

        `标记已改` 默认为 False（用于刚从磁盘加载完文件）；
        程序内部改写内容时应传 True，否则会误以为文件没变，
        后续保存/运行就会用磁盘上的旧内容。
        """
        self._载入中 = True
        self.setPlainText(文本)
        self._载入中 = False
        # 整份文本都换了，旧的折叠状态没有意义（userState 也随旧块一起没了）
        self._折叠数 = 0
        self.应用折叠()
        self.已改 = bool(标记已改)
        if hasattr(self, "主窗") and self.主窗 is not None:
            self.主窗.刷新标签(self)
            if self.已改 and self.主窗.当前 is self:
                self.主窗._刷新标题()


# 需要 QTextDocument 用于查找旗标
from PySide6.QtGui import QTextDocument  # noqa: E402
