# -*- coding: utf-8 -*-
"""核工坊的代码编辑器控件（PySide6 版）。

包含：行号栏、当前行高亮、缩进参考线、语法高亮、自动缩进、
      注释切换、查找定位。

与 tkinter 版行为一致，但代码量少很多 —— 高亮、选区、撤销栈都由 Qt 提供。
"""

import re

from PySide6.QtCore import QRect, QSize, Qt, Signal
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
        self.宽度 = 58
        self.setFixedWidth(self.宽度)

    def sizeHint(self):
        return QSize(self.宽度, 0)

    def paintEvent(self, 事件):
        色 = self.编辑器.主窗.主题
        绘 = QPainter(self)
        绘.fillRect(self.rect(), QColor(色["行号底"]))
        绘.setFont(self.编辑器.font())
        绘.setPen(QPen(QColor(色["行号字"])))

        编辑器 = self.编辑器
        块 = 编辑器.firstVisibleBlock()
        号 = 块.blockNumber() + 1
        顶 = int(
            编辑器.blockBoundingGeometry(块).translated(编辑器.contentOffset()).top()
        )
        行高 = 编辑器.fontMetrics().height()

        while 块.isValid() and 顶 <= 事件.rect().bottom():
            底 = 顶 + int(编辑器.blockBoundingRect(块).height())
            if 块.isVisible() and 底 >= 事件.rect().top():
                if 块.blockNumber() == 编辑器.当前行号():
                    绘.setPen(QPen(QColor(色["文本"])))
                else:
                    绘.setPen(QPen(QColor(色["行号字"])))
                绘.drawText(
                    0, 顶, self.宽度 - 10, 行高,
                    Qt.AlignRight | Qt.AlignVCenter, str(号),
                )
            块 = 块.next()
            顶 = 底
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
        self.制表宽 = 4

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
        self._更新行号宽()
        self._当前行变化()

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
        self._当前行变化()

    # —— 行号 ——

    def _更新行号宽(self, _=None):
        self.setViewportMargins(self.行号.宽度, 0, 0, 0)

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
        if getattr(self, "_载入中", False):
            return
        if not self.已改:
            self.已改 = True
            self.主窗.刷新标签(self)

    def paintEvent(self, 事件):
        super().paintEvent(事件)
        if self.主窗.显示缩进线:
            self._画缩进线()

    def _画缩进线(self):
        """按行画缩进参考线。

        PyCharm 的做法是：只在这一行**有缩进**时，于对应缩进层级画一小段竖线；
        空行、无缩进的行都不画。以前是整条通顶竖线，空区域也画满，很难看。
        """
        色 = self.主窗.主题
        绘 = QPainter(self.viewport())
        绘.setPen(QPen(QColor(色["缩进线"]), 1))
        字宽 = QFontMetrics(self.font()).horizontalAdvance(" ")
        宽 = 字宽 * self.制表宽
        if 宽 <= 0:
            return
        偏移 = int(self.contentOffset().x())
        可见顶 = 0
        可见底 = self.viewport().height()

        块 = self.firstVisibleBlock()
        视口偏移 = self.contentOffset().y()
        while 块.isValid():
            矩形 = self.blockBoundingGeometry(块).translated(self.contentOffset())
            顶 = int(矩形.top())
            if 顶 > 可见底:
                break
            高 = int(矩形.height())
            if 顶 + 高 >= 可见顶:
                文 = 块.text()
                if 文.strip():
                    # 这行有几级缩进，就画几段
                    前导 = len(文) - len(文.lstrip(" \t"))
                    级 = 前导 // self.制表宽
                    for i in range(1, 级 + 1):
                        x = 偏移 + 宽 * i
                        if x >= self.viewport().width():
                            break
                        绘.drawLine(x, 顶, x, 顶 + 高)
            块 = 块.next()

    # —— 键盘行为 ——

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
        # 自动配对括号与引号
        if 文本 in self.配对表 and not 事件.modifiers():
            self._自动配对(文本, self.配对表[文本])
            return
        # 输入右括号时，若紧邻的正是它，直接跳过（不重复插入）
        if 文本 and 文本 in self.配对表.values():
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
        """回车时保持缩进；若上一行以冒号结尾再缩进一级。"""
        光标 = self.textCursor()
        行文 = 光标.block().text()[: 光标.positionInBlock()]
        缩进 = len(行文) - len(行文.lstrip())
        额外 = self.制表宽 if 行文.rstrip().endswith(("：", ":")) else 0
        空格 = " " * (缩进 + 额外)
        # 先让 QPlainTextEdit 处理回车，再在「新光标位置」插入缩进。
        # 直接 insertPlainText 有时会插到旧位置，所以显式用 textCursor 插入。
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

    def 置文本(self, 文本):
        self._载入中 = True
        self.setPlainText(文本)
        self._载入中 = False
        self.已改 = False
        if hasattr(self, "主窗") and self.主窗 is not None:
            self.主窗.刷新标签(self)


# 需要 QTextDocument 用于查找旗标
from PySide6.QtGui import QTextDocument  # noqa: E402
