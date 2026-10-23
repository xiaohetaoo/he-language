# -*- coding: utf-8 -*-
"""核工坊的代码编辑器控件（PySide6 版）。

包含：行号栏、当前行高亮、缩进参考线、语法高亮、自动缩进、
      注释切换、查找定位。

与 tkinter 版行为一致，但代码量少很多 —— 高亮、选区、撤销栈都由 Qt 提供。
"""

import re

from PySide6.QtCore import QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor, QFont, QFontDatabase, QFontMetrics, QPainter, QPen, QTextCharFormat,
    QTextCursor, QSyntaxHighlighter, QKeyEvent,
)
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget

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

        关键字 = sorted(set(内核.关键词表) | {"核核"}, key=len, reverse=True)
        内置 = sorted(
            set(内核.函数表) | set(内核.方法表), key=len, reverse=True
        )

        def 带边界(词):
            return r"(?<![\w\u4e00-\u9fff])(?:%s)(?![\w\u4e00-\u9fff])" % "|".join(
                词
            )

        self.规则 = [
            (r"核核[^\n]*|#[^\n]*", 格式(主题色["注释"], 斜体=True)),
            (
                r'核?"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'',
                格式(主题色["字符串"]),
            ),
            (r"\b0[xX][0-9a-fA-F]+\b|\b\d[\d_]*(?:\.\d+)?\b", 格式(主题色["数字"])),
            (带边界(关键字), 格式(主题色["关键字"], 粗体=True)),
            (带边界(内置), 格式(主题色["内置"])),
            (r"(?<=核定义\s)[^\s(（:：]+", 格式(主题色["函数名"], 粗体=True)),
            (r"(?<=核类\s)[^\s(（:：]+", 格式(主题色["函数名"], 粗体=True)),
        ]

    def highlightBlock(self, 文本):
        if not self.开:
            return
        for 模式, 格式 in self.规则:
            for m in re.finditer(模式, 文本):
                self.setFormat(m.start(), m.end() - m.start(), 格式)


# ---------------------------------------------------------------------------
# 行号栏
# ---------------------------------------------------------------------------


class 行号区(QWidget):
    def __init__(self, 编辑器):
        super().__init__(编辑器)
        self.编辑器 = 编辑器
        # 宽度按「最大行号位数」自适应，至少 3 位（58px）。
        # 太窄时两位数就挤到边缘，正文看起来像被行号压住了。
        self.宽度 = 58
        self.setFixedWidth(self.宽度)

    def 按行号调整宽度(self, 总行数):
        位数 = max(3, len(str(max(1, 总行数))))
        新宽 = 16 + 位数 * 9
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
            块 = 块.next()
            顶 += 高
            号 += 1


# ---------------------------------------------------------------------------
# 编辑器
# ---------------------------------------------------------------------------


class 编辑器(QPlainTextEdit):
    """PyCharm 风格代码编辑器，带行号、当前行、缩进参考线。"""

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
        self.setTabStopDistance(
            QFontMetrics(字体).horizontalAdvance(" ") * self.制表宽
        )
        if hasattr(self, "行号"):
            self.行号.setFont(字体)
            self.行号.update()

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
        self._缩进线开 = bool(getattr(主窗, "显示缩进线", True))
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
        self.光标移动.emit()

    def _文本变化(self):
        """文本变了。这里只做最轻的记账，重的 UI 更新一律延后。

        教训：以前在这里同步调 `更新状态栏()` 和 `_刷新标题()`，
        它们会改状态栏文字和窗口标题，引起重排重绘并重入事件循环；
        连续快速输入（尤其配合输入法）时会丢字，用户看到的就是「吞字」。
        现在改成去抖：无论触发多少次，只在一个事件循环之后做一次。
        """
        if getattr(self, "_载入中", False):
            return
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
        if 文本 in self.配对表 and not 事件.modifiers() and not 组字中:
            self._自动配对(文本, self.配对表[文本])
            return
        if 组字中 and 文本 in self.配对表:
            # 组字期间这类按键交给输入法决定（它会把 ' 变成 ’ 之类），
            # 自己不能再插一个字符，否则上屏后多出个引号。
            事件.accept()
            return
        # 输入右括号时，若紧邻的正是它，直接跳过（不重复插入）
        if 文本 and 文本 in self.配对表.values() and not 组字中:
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
        """
        光标 = self.textCursor()
        行文 = 光标.block().text()[: 光标.positionInBlock()]
        缩进 = len(行文) - len(行文.lstrip())
        额外 = self.制表宽 if 行文.rstrip().endswith(("：", ":")) else 0
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

    def 切换注释(self):
        光标 = self.textCursor()
        起 = self.document().findBlock(光标.selectionStart()).blockNumber()
        止 = self.document().findBlock(光标.selectionEnd()).blockNumber()
        块们 = [self.document().findBlockByNumber(i) for i in range(起, 止 + 1)]
        有内容 = [b for b in 块们 if b.text().strip()]
        if not 有内容:
            return
        全注释 = all(b.text().lstrip().startswith("核核 ") for b in 有内容)
        游标 = self.textCursor()
        游标.beginEditBlock()
        for 块 in 块们:
            文 = 块.text()
            if 全注释:
                缩进 = len(文) - len(文.lstrip())
                若去掉 = 文[:缩进] + 文[缩进:].replace("核核 ", "", 1)
                游 = QTextCursor(块)
                游.movePosition(QTextCursor.StartOfBlock)
                游.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
                游.insertText(若去掉)
            else:
                if not 文.strip():
                    continue
                缩进 = len(文) - len(文.lstrip())
                游 = QTextCursor(块)
                游.movePosition(QTextCursor.StartOfBlock)
                游.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor, 缩进)
                游.insertText("核核 ")
        游标.endEditBlock()

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

    def 替换当前(self, 查找词, 替换词):
        """替换当前选中的匹配项（没有选中就先找一个）。"""
        游 = self.textCursor()
        if not 游.hasSelection() or 游.selectedText() != 查找词:
            if not self.查找下一个(查找词):
                return False
            游 = self.textCursor()
        游.insertText(替换词)
        self.setTextCursor(游)
        return True

    def 全部替换(self, 查找词, 替换词):
        """替换全部匹配项，返回替换次数。"""
        if not 查找词:
            return 0
        次数 = 0
        游 = QTextCursor(self.document())
        游.beginEditBlock()
        游.movePosition(QTextCursor.Start)
        while True:
            self.setTextCursor(游)
            if not self.find(查找词):
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
        self.已改 = bool(标记已改)
        if hasattr(self, "主窗") and self.主窗 is not None:
            self.主窗.刷新标签(self)
            if self.已改 and self.主窗.当前 is self:
                self.主窗._刷新标题()


# 需要 QTextDocument 用于查找旗标
from PySide6.QtGui import QTextDocument  # noqa: E402
