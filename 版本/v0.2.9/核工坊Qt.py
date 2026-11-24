# -*- coding: utf-8 -*-
"""核工坊 Qt 版主窗口 —— 严格模仿 PyCharm 新 UI。

布局（自上而下、自左而右）：
    顶部单行：图标 | ☰ 菜单 | 项目名 | 版本控制 | …… | ▶ 运行 | ⚙ | 搜索 | 窗口按钮
    主体：左侧竖条(项目/结构/运行/设置) | 项目树 | 编辑器 | 右侧对照表
    底部：运行窗口（含输入行）
    状态栏：项目 | 提示 | 行/列 | 编码 | 缩进

内核（转译/执行）全部复用 核.py，一行不改。
"""

import codecs
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import (
    QAction, QBrush, QColor, QIcon, QKeySequence, QPixmap, QShortcut, QTextCursor,
)
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMenu, QMessageBox, QPlainTextEdit, QProxyStyle, QSizePolicy,
    QSplitter, QStyle, QTabBar, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

import 主题
import 配置
import 版本控制
from 编辑器 import 编辑器

这里 = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, 这里)

import 核  # noqa: E402


class _版本任务(QRunnable):
    """跑一次 git 状态查询。由 版本查询器 丢进线程池。"""

    def __init__(self, 查询器, 目录):
        super().__init__()
        self._查询器 = 查询器
        self._目录 = 目录
        self.setAutoDelete(True)

    def run(self):
        try:
            状态 = 版本控制.状态(self._目录)
        except Exception as e:  # noqa: BLE001 - 查询失败也必须回一个结果
            状态 = dict(版本控制.状态(""))
            状态["原因"] = "读取失败：%s" % e
        self._查询器._完成(self._目录, 状态)


class 版本查询器(QObject):
    """在后台线程里读 git 状态，结果用信号送回主线程。

    为什么必须挪出 GUI 线程：版本控制.状态() 串行跑 4 个 git 子进程
    （--is-inside-work-tree、rev-parse、status --porcelain、rev-list），
    每个超时上限 6 秒。以前 保存() 末尾直接同步调用它 —— 每按一次
    Ctrl+S 都要在 GUI 线程上等 git 返回。本仓库（150 个 blob）实测
    单次 272ms，仓库变大、放进网络盘、或被杀毒软件逐个文件扫描时
    就是秒级冻结。启动时改用 singleShot(0) 只是把它推迟到事件队列末尾，
    仍然在主线程同步跑，没解决卡顿。

    合并策略：同一时刻只允许一个查询在飞。飞行期间来的请求只记下
    「还要再查一次最新的」，落地后自动补跑 —— 连按保存不会堆出一串
    并发子进程，也不会把界面淹在一堆过期结果里。
    """

    好了 = Signal(object, str)  # (状态 dict, 这次查的是哪个目录)

    def __init__(self, 父=None):
        super().__init__(父)
        self._池 = QThreadPool(self)
        self._池.setMaxThreadCount(1)
        self._锁 = threading.Lock()
        self._飞行中 = False
        self._待查 = None
        self._停 = False

    def 查(self, 目录):
        with self._锁:
            if self._停:
                return
            if self._飞行中:
                self._待查 = 目录
                return
            self._飞行中 = True
        self._池.start(_版本任务(self, 目录))

    def _完成(self, 目录, 状态):
        """在工作线程里被调用 —— 只碰锁和信号，不碰界面控件。"""
        with self._锁:
            还有 = self._待查
            self._待查 = None
            self._飞行中 = False
            if self._停:
                return
        try:
            self.好了.emit(状态, 目录)
        except RuntimeError:
            # 窗口已经先被销毁（关掉窗口、测试里 deleteLater），
            # 底层 C++ 对象没了，信号发不出去 —— 直接放弃这次结果。
            return
        if 还有 is not None:
            self.查(还有)

    def 停(self):
        """退出前调用：不再回填结果，并等正在跑的任务收尾。"""
        with self._锁:
            self._停 = True
            self._待查 = None
        self._池.waitForDone(3000)


def _还活着(对象):
    """PySide6 的包装对象还在不在？

    Python 层还拿着引用不代表底层 C++ 对象还在 —— 只要有人调过
    deleteLater（关闭文档就是这么干的），下一轮事件循环它就被销毁，
    之后读任何属性都会抛
        RuntimeError: Internal C++ object (...) already deleted
    所有「异步回调里再用旧引用」的地方都要先过这一关。
    """
    try:
        from shiboken6 import isValid
    except ImportError:       # 理论上不会发生，PySide6 一定带 shiboken6
        return True
    return isValid(对象)


def _判定保存答复(答):
    """把 QMessageBox 的各种返回统一成三条明确的路：save / discard / cancel。

    **这里是数据丢失级 bug 的根治点**：用户点标题栏的 X 或按 Esc 关掉
    「要保存吗」对话框时，QMessageBox 返回的是 `NoButton`（值是 0），
    不是 `Cancel`。老代码写的是 `if 答 == QMessageBox.Cancel: return False`
    －－ 0 不等于 Cancel，于是「关掉对话框」被当成「继续」，
    未保存的改动**无声无息丢掉**。多文档时还会把当前这份当「不保存」
    继续去问下一个。

    所以判定一律走白名单：只认 Save/Discard（以及等价的 Yes/No），
    其余（含 NoButton、以及将来新增的任何返回值）一律按取消处理。
    """
    if 答 in (QMessageBox.Save, QMessageBox.Yes):
        return "save"
    if 答 in (QMessageBox.Discard, QMessageBox.No):
        return "discard"
    return "cancel"


def _问保存三选(父, 标题, 文本, 默认=QMessageBox.Save):
    """模态地问「保存 / 不保存 / 取消」，返回 save / discard / cancel。

    与 `QMessageBox.question` 的区别：
      · 按钮文字是中文（保存 / 不保存 / 取消）；
      · **显式 setEscapeButton(Cancel)**：按 Esc 一定落到「取消」，
        而不是靠平台默认（有的平台默认是 No，等于悄悄放弃改动）；
      · 返回的是三选之一的语义值，不再让调用方去比标准按钮枚举。
    """
    框 = QMessageBox(父)
    框.setWindowTitle(标题)
    框.setText(文本)
    框.setIcon(QMessageBox.Question)
    框.setStandardButtons(QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
    框.setDefaultButton(默认)
    框.setEscapeButton(QMessageBox.Cancel)
    框.button(QMessageBox.Save).setText("保存")
    框.button(QMessageBox.Discard).setText("不保存")
    框.button(QMessageBox.Cancel).setText("取消")
    return _判定保存答复(框.exec())


class _控件样式(QProxyStyle):
    """只接管「复选框指示器」的代理样式（P2-24）。

    为什么需要它：QSS 里 `QCheckBox::indicator` 一旦写了 background，
    整个指示器子控件就交给样式表画 —— 而 QSS **画不出对勾**
    （没有图片资源，也不支持 CSS 的 border 拼三角形）。
    于是选中态只剩一块纯色方块，和未选中态仅靠颜色区分，
    色弱用户和小字号下基本分不出来。

    这里用 QProxyStyle 自绘：底 + 边框 + 一条真正的对勾路径，
    尺寸固定 14×14（界面控件不跟随编辑器字号，见 pixelMetric）。
    其它所有绘制原样交给基础样式，不影响别处。
    """

    #: 当前配色（由 主窗 在换主题时写入）
    配色 = {}

    def drawPrimitive(self, 元素, 选项, 画笔, 控件=None):
        if 元素 == QStyle.PE_IndicatorCheckBox:
            self._画复选框(选项, 画笔)
            return
        super().drawPrimitive(元素, 选项, 画笔, 控件)

    def pixelMetric(self, 度量, 选项=None, 控件=None):
        """复选框指示器**固定** 14×14（P2-2）。

        上一版这里声称「随字号 13→24 缩放」，其实读的是
        `选项.fontMetrics` —— 那是 QCheckBox 自己的字体，来自应用默认
        9pt，根本不跟编辑器字号走。实测 12 号与 40 号字号下
        sizeHint 都是 34x13、指示器都是 13px，两张证据截图逐像素相同。
        声称能缩放而实际不能，比不缩放更糟。

        现在的设计是明确的：**界面控件是固定字号，只有编辑区正文跟随
        字号**（和 控制台 / 版本历史 / diffView 的处理一致）。
        所以指示器就是固定 14px，不再假装缩放。
        """
        if 度量 in (QStyle.PM_IndicatorWidth, QStyle.PM_IndicatorHeight):
            return 14
        return super().pixelMetric(度量, 选项, 控件)

    def _画复选框(self, 选项, 画笔):
        from PySide6.QtCore import QPointF, Qt as _Qt
        from PySide6.QtGui import QColor, QPainterPath, QPen

        区域 = 选项.rect.adjusted(1, 1, -1, -1)
        边 = min(区域.width(), 区域.height())
        if 边 <= 0:
            return
        # 摆正成正方形（QSS 去掉之后光标区可能给一个偏宽的区域）
        区域.setWidth(边)
        状态 = 选项.state
        选中 = bool(状态 & QStyle.State_On)
        半选 = bool(状态 & QStyle.State_NoChange)
        可用 = bool(状态 & QStyle.State_Enabled)
        配色 = self.配色 or {}
        强调 = QColor(配色.get("强调", "#3574F0"))
        # 未选中态的边框不能用 边框 色（#393B40）：它和面板底只差一点点，
        # 在深色主题上看上去就是「一个黑方块」，用户分不清那是选择框
        # 还是选中的实心块。用「次要文本」这一档（深 #B2B6BE / 浅 #5F6672）
        # 才能一眼看出「这里有个空框可以勾」。
        边框 = QColor(配色.get("次要文本", "#B2B6BE"))
        底 = QColor(配色.get("编辑器", "#1E1F22"))
        # 勾线用白色，**不跟「文本」色走**：选中态的底是强调蓝(#3574F0)，
        # 深色主题的文本色 #DFE1E5 在上面 3.27:1、浅色主题的 #1F2329 更是
        # 只有 3.69:1 且是「深字压蓝底」，两套主题的勾看起来一深一浅。
        # 白勾在两套主题下都是 4.28:1，观感也统一（禁用态另算）。
        字 = QColor("#FFFFFF")
        if not 可用:
            强调 = 强调.darker(160)
            边框 = 边框.darker(130)
            字 = QColor(配色.get("禁用文本", "#6F737A"))

        画笔.save()
        画笔.setRenderHint(画笔.RenderHint.Antialiasing, True)
        画笔.setPen(QPen(强调 if 选中 or 半选 else 边框, 1.2))
        画笔.setBrush(强调 if 选中 or 半选 else 底)
        半径 = max(3.0, 边 * 0.22)
        画笔.drawRoundedRect(区域, 半径, 半径)

        if 选中 or 半选:
            路径 = QPainterPath()
            if 半选:
                # 半选：一条短横线（三态里「部分选中」的通用画法）
                左 = 区域.left() + 边 * 0.25
                右 = 区域.right() - 边 * 0.25
                中 = 区域.center().y()
                路径.moveTo(QPointF(左, 中))
                路径.lineTo(QPointF(右, 中))
            else:
                # 对勾：两段折线，比例按边长算，缩放不变形
                路径.moveTo(QPointF(区域.left() + 边 * 0.24, 区域.top() + 边 * 0.52))
                路径.lineTo(QPointF(区域.left() + 边 * 0.42, 区域.top() + 边 * 0.70))
                路径.lineTo(QPointF(区域.left() + 边 * 0.77, 区域.top() + 边 * 0.30))
            画笔.setPen(QPen(字, max(1.6, 边 * 0.14), _Qt.SolidLine, _Qt.RoundCap, _Qt.RoundJoin))
            画笔.setBrush(_Qt.NoBrush)
            画笔.drawPath(路径)
        画笔.restore()


def 安装控件样式():
    """把 _控件样式 装到当前 QApplication 上（幂等）。"""
    应用 = QApplication.instance()
    if 应用 is None:
        return None
    已有 = getattr(应用, "_核控件样式", None)
    if 已有 is not None:
        return 已有
    样式 = _控件样式(应用.style())
    应用.setStyle(样式)
    应用._核控件样式 = 样式
    return 样式


class 省略标签(QLabel):
    """放不下时用省略号收尾、并且把全文放 tooltip 的 QLabel（P2-21）。

    以前状态栏两个 QLabel 都是普通 QLabel：长文本（比如
    「配置文件有 3 处不合法，已回退默认：…」）会把 sizeHint 撑到 693px，
    实际只有 489px 可用 —— Qt 直接**硬裁**，没有省略号，
    而且把右边的编码/行列挤出可视区。用户看到的是一句断在半截的话，
    也分不清右边那栏是没了还是没刷新。
    """

    def __init__(self, 文本="", 父=None):
        super().__init__(文本, 父)
        self._全文 = 文本
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setMinimumWidth(0)

    def 设全文(self, 文本):
        self._全文 = 文本 or ""
        self.setToolTip(self._全文)
        self._重排()

    def resizeEvent(self, 事件):
        super().resizeEvent(事件)
        self._重排()

    def _重排(self):
        可用 = max(0, self.width())
        显示 = self.fontMetrics().elidedText(
            self._全文, Qt.ElideRight, 可用)
        # 用 super 直接写，避免 setText 递归
        super().setText(显示)

    def text(self):  # noqa: A003 - 与 QLabel 同名，语义就是「显示出来的文本」
        return super().text()

    def 全文(self):
        return self._全文


def 图标路径(名):
    return os.path.join(这里, "素材", 名)


#: 项目树里不显示的条目。
#: `_启动Qt.py` 是打包脚本自动生成的临时入口（已在 .gitignore 里），
#: 留在项目树里只会让用户困惑「这个文件是干什么的」。
_隐藏项 = (
    "__pycache__", "build", "dist", "build_v001", "release",
    "_启动Qt.py", "工坊配置.json", "未定义.txt",
)


def _默认项目目录():
    """打包版不能用 _MEIPASS 临时目录当项目根。

    exe 双击时工作目录是 exe 所在处；若在 dist 里则上移一级，
    这样用户能看到源码与例子，而不是一堆解包临时文件。
    """
    if getattr(sys, "frozen", False):
        目录 = os.path.dirname(os.path.abspath(sys.executable))
        if os.path.basename(目录).lower() in ("dist", "release", "build"):
            父 = os.path.dirname(目录)
            if os.path.isdir(父):
                return 父
        if os.path.isdir(目录):
            return 目录
    return os.getcwd()


class 窗口钮(QLabel):
    """顶行右上角的最小化 / 最大化 / 关闭。

    尺寸与「同一条顶行里的其他控件」对齐（0.2.7 整理）：
    顶行高 44，所有控件都在垂直居中位置上。
      · 窗口钮 46x32，居中 → y = (44-32)/2 = 6
      · 搜索框高 28，居中 → y = (44-28)/2 = 8
    两者高度不同是正常的（按钮要比输入框高一点才好点），
    但**都必须居中**；以前搜索框直接由布局摆放，窗口钮用 setFixedSize，
    在 44px 的顶行里一高一低，右半边看起来是斜的。
    """

    宽 = 46
    高 = 32

    def __init__(self, 字, 提示, 关闭类=False, 父=None):
        super().__init__(字, 父)
        self.setObjectName("关闭钮" if 关闭类 else "窗口钮")
        self.setToolTip(提示)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedSize(self.宽, self.高)
        self.setCursor(Qt.PointingHandCursor)


class 带箭头下拉框(QComboBox):
    """下拉框：自带画出来的小三角箭头。

    为什么不用 QSS 的 `::down-arrow`：
      · QSS 不支持 CSS 里「用透明边框拼三角形」那套写法，写了会渲染成
        一个实心方块（实测是一个 8x8 的灰块，很难看）；
      · 用图片的话，单文件打包后 QSS 里的相对路径会失效。
    所以箭头在这里自己画，颜色跟主题走，深/浅色都能看清。
    """

    def __init__(self, 父=None):
        super().__init__(父)
        self.箭头色 = "#B2B6BE"

    def 设箭头色(self, 色):
        self.箭头色 = 色
        self.update()

    def paintEvent(self, 事件):
        super().paintEvent(事件)
        from PySide6.QtCore import QPointF, Qt as _Qt
        from PySide6.QtGui import QBrush, QColor, QPainter, QPolygonF

        绘 = QPainter(self)
        绘.setRenderHint(QPainter.Antialiasing, True)
        绘.setPen(_Qt.NoPen)
        绘.setBrush(QBrush(QColor(self.箭头色)))
        # 贴在右侧，垂直居中，尺寸固定 4x5（太小看不出，太大会挤文字）
        右 = self.width() - 12
        中 = self.height() / 2
        三角 = QPolygonF([
            QPointF(右 - 4, 中 - 2.5),
            QPointF(右 + 4, 中 - 2.5),
            QPointF(右, 中 + 3.5),
        ])
        绘.drawPolygon(三角)
        绘.end()


class 顶行(QWidget):
    """顶部单行：PyCharm 新 UI 把菜单、工具栏、搜索合并到一行。"""

    def __init__(self, 主窗):
        super().__init__(主窗)
        self.主窗 = 主窗
        self._拖点 = None
        self.setObjectName("topRow")
        self.setFixedHeight(主题.高_顶行)

        布局 = QHBoxLayout(self)
        布局.setContentsMargins(主题.内边距, 0, 0, 0)
        布局.setSpacing(主题.间距_紧)

        标 = QLabel()
        标.setObjectName("brandMark")
        self.品牌 = 标
        标.setToolTip("核工坊")
        # 用大图让 Qt 自己平滑缩放。
        # 千万不能用 核图标_32.png 这种预缩好的小图：32px 版本只有 3% 的
        # 不透明像素、16px 版本是 0% —— 细轨道线在预缩时被抹掉了，
        # 画上去几乎是空的，看起来像图标丢了。
        # 26px 是顶栏高度 44 下仍能看清原子轨道与彩色立方体的最小尺寸。
        尺寸 = 26
        self._品牌图 = 缩放品牌图(尺寸)
        if self._品牌图 is not None:
            标.setPixmap(self._品牌图)
        布局.addWidget(标)

        # 标志后面跟「核工坊」字样 —— 这是用户明确要求保留的，别改
        self.品牌字 = QLabel("核工坊")
        self.品牌字.setObjectName("品牌字")
        self.品牌字.setCursor(Qt.PointingHandCursor)
        self.品牌字.setToolTip("核工坊 v%s" % 核.版本)
        self.品牌字.mousePressEvent = lambda e: 主窗.弹主菜单(self.品牌字)
        布局.addWidget(self.品牌字)
        布局.addSpacing(8)

        self.菜单钮 = QLabel("☰")
        self.菜单钮.setObjectName("menuBtn")
        self.菜单钮.setCursor(Qt.PointingHandCursor)
        self.菜单钮.setToolTip("主菜单")
        self.菜单钮.mousePressEvent = lambda e: 主窗.弹主菜单(self.菜单钮)
        布局.addWidget(self.菜单钮)
        布局.addSpacing(4)

        self.项目名 = QLabel("核语言")
        self.项目名.setObjectName("projectName")
        self.项目名.setCursor(Qt.PointingHandCursor)
        self.项目名.mousePressEvent = lambda e: 主窗.弹出项目菜单(self.项目名)
        布局.addWidget(self.项目名)

        布局.addSpacing(10)
        # 版本控制：显示当前分支和改动数，点开看具体改了哪些文件。
        # 原来这里是个死的占位标签，点一下只弹一句「尚未接入 git」。
        self.版本钮 = QLabel("⎇ 版本控制")
        self.版本钮.setObjectName("topBtn")
        self.版本钮.setCursor(Qt.PointingHandCursor)
        self.版本钮.setToolTip("版本控制（只读：分支与改动文件）")
        self.版本钮.mousePressEvent = lambda e: 主窗.版本控制面板()
        布局.addWidget(self.版本钮)

        布局.addStretch(1)

        self.运行钮 = QLabel()
        self.运行钮.setObjectName("runBtn")
        self.运行钮.setCursor(Qt.PointingHandCursor)
        self.运行钮.setToolTip("运行（F5）")
        self.运行钮.setAlignment(Qt.AlignCenter)
        # 给一个「正方形可点区域」而不是只包住 14px 的图标：
        # 以前设的是 setFixedWidth(30) 却没有高度约束，QLabel 会撑满顶行高（44），
        # 于是可点区是个 30x44 的竖条 —— 看起来像图标上下各空一大块，
        # 和右边等高的搜索框（28）视觉重心也不一致。
        self.运行钮.setFixedSize(32, 32)
        self.运行钮.mousePressEvent = lambda e: 主窗.运行()
        布局.addWidget(self.运行钮)
        布局.addSpacing(主题.间距_紧)

        # 设置入口只在左侧竖条底部保留一个（顶行不再重复放齿轮）

        self.搜索 = QLineEdit()
        self.搜索.setObjectName("searchBox")
        self.搜索.setPlaceholderText("搜索（回车找下一处）")
        self.搜索.setFixedWidth(170)
        self.搜索.returnPressed.connect(主窗.搜索回车)
        布局.addWidget(self.搜索)
        布局.addSpacing(主题.间距_紧)

        self.最小化 = 窗口钮("—", "最小化")
        self.最大化 = 窗口钮("□", "最大化 / 还原")
        self.关闭 = 窗口钮("✕", "关闭", 关闭类=True)
        for 钮 in (self.最小化, self.最大化, self.关闭):
            布局.addWidget(钮)
        self.最小化.mousePressEvent = lambda e: 主窗.showMinimized()
        self.最大化.mousePressEvent = lambda e: self.切最大化()
        self.关闭.mousePressEvent = lambda e: 主窗.退出()

    def 刷新图标(self, 主题表=None):
        """重画顶行的运行三角。品牌标记用原图，不在这里改。"""
        表 = 主题表 or {}
        运色 = 表.get("图标运行", "#4CAF6E")
        self.运行钮.setPixmap(画图标("三角", 运色, 14))

    def 切最大化(self):
        if self.主窗.isMaximized():
            self.主窗.showNormal()
        else:
            self.主窗.showMaximized()
        self.同步窗口钮()

    def 同步窗口钮(self):
        """按真实窗态回填「最大化 / 还原」那个字形。

        以前只有点这个按钮（或双击顶栏）才会改字形：用户用 Win+↑、
        拖到屏幕上沿贴边、或从任务栏还原时，窗口已经最大化了，
        按钮却还画着 □ —— 顶栏状态和窗口状态对不上。
        主窗.changeEvent 里也会调它，任何一条改窗态的路都能同步。
        """
        try:
            self.最大化.setText("❐" if self.主窗.isMaximized() else "□")
        except (AttributeError, RuntimeError):
            pass

    def 设项目名(self, 文本):
        self.项目名.setText(文本)

    def mousePressEvent(self, 事件):
        if 事件.button() == Qt.LeftButton:
            self._拖点 = (
                事件.globalPosition().toPoint() - self.主窗.frameGeometry().topLeft()
            )
        super().mousePressEvent(事件)

    def mouseMoveEvent(self, 事件):
        if (
            self._拖点 is not None
            and 事件.buttons() & Qt.LeftButton
            and not self.主窗.isMaximized()
        ):
            self.主窗.move(事件.globalPosition().toPoint() - self._拖点)
        super().mouseMoveEvent(事件)

    def mouseReleaseEvent(self, 事件):
        self._拖点 = None
        super().mouseReleaseEvent(事件)

    def mouseDoubleClickEvent(self, 事件):
        self.切最大化()
        super().mouseDoubleClickEvent(事件)


def 缩放品牌图(边长):
    """把工作室标志（原子 + 彩色立方体）按目标边长平滑缩放。

    直接用最原始的大图（图标PNG，530x470），绝不用 素材/核图标_16/24/32.png
    这类预缩小图：实测 32px 版只有 3% 不透明像素、16px 版是 0%，
    细轨道线在预缩阶段就被抹平了，贴上去几乎是空白。
    """
    源 = 图标路径("核图标.png")
    if not os.path.exists(源):
        源 = 图标路径("核图标_256.png")
    if not os.path.exists(源):
        return None
    原 = QPixmap(源)
    if 原.isNull():
        return None
    return 原.scaled(
        边长, 边长, Qt.KeepAspectRatio, Qt.SmoothTransformation
    )


def 画图标(形状, 颜色, 大小=18):
    """自己画竖条图标。

    以前用 ▤ ☰ ▶ ⚙ 这类符号当图标，全是细线条，缩到 18px 后彼此分不清
    （用户反馈「功能图标太像了，没有区分度」）。这里改成实心几何形状 +
    各自独立的颜色：文件夹/列表一眼能分辨，颜色再拉开一层区分。
    """
    from PySide6.QtCore import QPointF, QRectF
    from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen, QPolygonF

    倍 = 2  # 按 2 倍画再缩放，边缘更干净
    图 = QPixmap(大小 * 倍, 大小 * 倍)
    图.fill(Qt.transparent)
    画 = QPainter(图)
    画.setRenderHint(QPainter.Antialiasing, True)
    色 = QColor(颜色)
    S = 大小 * 倍
    单位 = S / 18.0

    def 点(x, y):
        return QPointF(x * 单位, y * 单位)

    if 形状 == "文件夹":
        # 后板（带标签）
        路 = QPainterPath()
        路.moveTo(点(1.5, 4.5))
        路.lineTo(点(6.5, 4.5))
        路.lineTo(点(8.0, 6.5))
        路.lineTo(点(16.5, 6.5))
        路.lineTo(点(16.5, 14.5))
        路.lineTo(点(1.5, 14.5))
        路.closeSubpath()
        画.setPen(Qt.NoPen)
        画.setBrush(QBrush(色))
        画.drawPath(路)
        # 前板（略亮），形成文件夹的层次
        亮 = QColor(色).lighter(125)
        画.setBrush(QBrush(亮))
        画.drawRoundedRect(QRectF(点(1.5, 7.5), 点(16.5, 14.5)), 1.6 * 单位, 1.6 * 单位)

    elif 形状 == "列表":
        # 左侧三个圆点 + 右侧三条横线（结构/大纲）
        画.setPen(Qt.NoPen)
        画.setBrush(QBrush(色))
        for i, y in enumerate((4.5, 9.0, 13.5)):
            画.drawEllipse(点(3.0, y), 1.5 * 单位, 1.5 * 单位)
            宽 = 8.5 if i != 1 else 6.0  # 中间那条短一点，更像大纲
            画.drawRoundedRect(QRectF(点(6.5, y - 1.0), 点(6.5 + 宽, y + 1.0)), 0.8 * 单位, 0.8 * 单位)

    elif 形状 == "三角":
        # 实心播放三角
        画.setPen(Qt.NoPen)
        画.setBrush(QBrush(色))
        画.drawPolygon(QPolygonF([点(6.0, 4.0), 点(14.5, 9.0), 点(6.0, 14.0)]))

    elif 形状 == "终端":
        # 运行窗口（控制台面板）的开关。
        # 以前这里也用播放三角，和顶行「运行」按钮的三角撞脸，分不出哪个是
        # 执行、哪个只是开面板；改成终端窗口造型，一眼能区分。
        画.setPen(QPen(色, 1.5 * 单位))
        画.setBrush(Qt.NoBrush)
        画.drawRoundedRect(QRectF(点(2.0, 3.5), 点(16.0, 14.5)), 1.8 * 单位, 1.8 * 单位)
        画.setPen(QPen(色, 1.6 * 单位, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        路 = QPainterPath()
        路.moveTo(点(5.0, 7.2))
        路.lineTo(点(7.4, 9.0))
        路.lineTo(点(5.0, 10.8))
        画.drawPath(路)
        画.setPen(QPen(色, 1.6 * 单位, Qt.SolidLine, Qt.RoundCap))
        画.drawLine(点(9.2, 11.0), 点(13.0, 11.0))

    elif 形状 == "齿轮":
        画.setPen(QPen(色, 1.7 * 单位))
        画.setBrush(Qt.NoBrush)
        # 用「滑块」造型代替齿轮：三条带柄横线，小尺寸下更清楚
        for y, 柄 in ((5.0, 6.5), (9.0, 11.5), (13.0, 7.5)):
            画.drawLine(点(3.0, y), 点(15.0, y))
            画.setBrush(QBrush(色))
            画.drawEllipse(点(柄, y), 1.7 * 单位, 1.7 * 单位)
            画.setBrush(Qt.NoBrush)

    elif 形状 == "圆点":
        画.setPen(Qt.NoPen)
        画.setBrush(QBrush(色))
        画.drawEllipse(点(9.0, 9.0), 4.0 * 单位, 4.0 * 单位)

    elif 形状 == "原子":
        # 品牌标记：用矢量画原子（两条交叉轨道 + 原子核）。
        # 原先用 素材/核图标_32.png 缩到 20px，但那张图本身 97% 是透明像素
        # （细轨道线在高分辨率下描边），缩到 20px 后几乎什么都没画上，
        # 在深色底上等于看不见。改成矢量后任何尺寸都清楚，且随主题换色。
        画.setPen(QPen(色, 1.6 * 单位))
        画.setBrush(Qt.NoBrush)
        画.save()
        画.translate(点(9.0, 9.0))
        画.drawEllipse(QPointF(0, 0), 7.0 * 单位, 3.0 * 单位)
        画.rotate(60)
        画.drawEllipse(QPointF(0, 0), 7.0 * 单位, 3.0 * 单位)
        画.restore()
        画.setPen(Qt.NoPen)
        画.setBrush(QBrush(色))
        画.drawEllipse(点(9.0, 9.0), 2.3 * 单位, 2.3 * 单位)

    画.end()
    return 图.scaled(大小, 大小, Qt.KeepAspectRatio, Qt.SmoothTransformation)


class 左竖条(QWidget):
    """左侧竖排图标栏（PyCharm 的工具窗口按钮）。"""

    def __init__(self, 主窗):
        super().__init__(主窗)
        self.主窗 = 主窗
        self.setObjectName("leftRail")
        self.setFixedWidth(44)

        布局 = QVBoxLayout(self)
        # 左右边距必须按「竖条宽 - 按钮宽」对半分：
        # 以前用的是 主题.内边距(12)，而竖条固定 44、按钮固定 32 ——
        # 12+32+12=56 > 44，布局挤不下就保住左边距、把右边距吃掉，
        # 图标于是贴着竖条右边线、左侧空 12px，整列看着是歪的。
        横边 = max(0, (44 - 32) // 2)
        布局.setContentsMargins(横边, 主题.内边距, 横边, 主题.内边距)
        布局.setSpacing(主题.间距)

        # 每个按钮用不同「形状 + 颜色」，避免全是线条符号看不出区别。
        # 颜色不写死，改成主题表里的键，主题一换整体重画。
        self.钮们 = {}
        self._图标表 = [
            ("项目", "文件夹", "图标项目", "项目栏（Ctrl+1）", lambda: 主窗.切换项目栏()),
            ("结构", "列表", "图标结构", "语法对照表（Ctrl+2）", lambda: 主窗.切换对照表()),
            ("运行", "终端", "图标运行", "运行窗口（Ctrl+3）", lambda: 主窗.切换运行窗()),
        ]
        for 键, 形状, 色键, 提示, 命令 in self._图标表:
            钮 = QLabel()
            钮.setObjectName("railBtn")
            钮.setAlignment(Qt.AlignCenter)
            钮.setFixedSize(32, 32)
            钮.setCursor(Qt.PointingHandCursor)
            钮.setToolTip(提示)
            钮.mousePressEvent = lambda e, c=命令: c()
            布局.addWidget(钮)
            self.钮们[键] = 钮

        布局.addStretch(1)

        # 设置放最底下，和 PyCharm 一致；顶行不再重复放齿轮
        设 = QLabel()
        设.setObjectName("railBtn")
        设.setAlignment(Qt.AlignCenter)
        设.setFixedSize(32, 32)
        设.setCursor(Qt.PointingHandCursor)
        设.setToolTip("设置（Ctrl+,）")
        设.mousePressEvent = lambda e: 主窗.打开设置()
        布局.addWidget(设)
        self.钮们["设置"] = 设

        self.状态点 = QLabel()
        self.状态点.setObjectName("railBtn")
        self.状态点.setAlignment(Qt.AlignCenter)
        self.状态点.setFixedSize(32, 32)
        self.状态点.setToolTip("运行状态")
        布局.addWidget(self.状态点)
        #: 当前运行状态：空闲 / 运行
        self._状态 = "空闲"

        self.刷新图标()
        self.设状态点("空闲")

    def 设状态点(self, 状态):
        """切换竖条底部状态点的颜色。

        这个点是 画图标("圆点") 生成的 **QPixmap**，不是文字 ——
        以前用 setStyleSheet("color: …") 改它，QSS 的 color 对 pixmap
        毫无作用，所以「运行中」那个点永远是绿的，视觉反馈等于不存在。
        要改就得按新颜色重画一张。
        """
        self._状态 = 状态
        表 = getattr(self.主窗, "主题", {}) or {}
        if 状态 == "运行":
            色 = 表.get("强调", "#3574F0")
            self.状态点.setToolTip("正在运行")
        else:
            色 = 表.get("图标状态点", "#6AAB73")
            self.状态点.setToolTip("运行状态：空闲")
        self.状态点.setPixmap(画图标("圆点", 色))

    def 刷新图标(self, 主题表=None):
        """按当前主题重画竖条图标。"""
        表 = 主题表 or getattr(self.主窗, "主题", {}) or {}
        取 = lambda 键, 备: 表.get(键, 备)
        形状表 = {键: 形状 for 键, 形状, _, _, _ in self._图标表}
        self.钮们["项目"].setPixmap(画图标(形状表["项目"], 取("图标项目", "#3574F0")))
        self.钮们["结构"].setPixmap(画图标(形状表["结构"], 取("图标结构", "#B58EF8")))
        self.钮们["运行"].setPixmap(画图标(形状表["运行"], 取("图标运行", "#4CAF6E")))
        self.钮们["设置"].setPixmap(画图标("齿轮", 取("图标设置", "#9DA0A8")))
        # 状态点的颜色由运行状态决定，不能在这里无条件重置成空闲色
        self.设状态点(getattr(self, "_状态", "空闲"))


class 主窗(QMainWindow):
    def __init__(self):
        super().__init__()
        self.内核 = 核
        self.配置 = 配置.读配置()
        self.主题名 = self.配置.get("主题", "深色")
        self.主题 = 主题.取主题(self.主题名)
        # 配置里存的值可能来自旧版本（旧范围只到 22）或被手改过，
        # 一律夹进当前允许范围，否则会拿到 60pt 这种排不下的字号。
        self.字号 = 主题.夹字号(self.配置.get("字号", 12))
        # 配置.py 已经做过 schema 校验，这里再兜一层强制转换。
        # 不是多此一举：配置对象在运行期也会被 应用设置/设制表宽 等
        # 直接改写，代码里任何一处写进坏值，都该在用的地方挡住，
        # 而不是指望上游永远干净（P1-7 的崩溃就是从 int("abc") 来的）。
        self.制表宽 = self._安全制表宽(self.配置.get("制表宽", 4))
        self.显示缩进线 = self.配置.get("缩进线", True) is not False
        self.显示行号 = self.配置.get("行号", True) is not False
        self.自动高亮 = self.配置.get("自动高亮", True) is not False
        self.最近 = [x for x in self.配置.get("最近", [])
                     if isinstance(x, str)] if isinstance(
            self.配置.get("最近", []), list) else []
        self.文档集 = []
        self.当前 = None
        项目 = self.配置.get("项目目录")
        self.项目目录 = 项目 if isinstance(项目, str) and 项目.strip() else _默认项目目录()
        #: 「持久配置里的项目目录」与「本次会话正在看的项目目录」分开记（P1-14）。
        #: 拖一个文件夹进来只是想看看，不该把它永久写进配置；
        #: 以前拖放路径先把 self.配置["项目目录"] 还原、再 存配置()，
        #: 但 self.项目目录 已经被 装载项目树() 改掉了 —— 下一次
        #: 存配置()（退出、改字号、应用设置）又把会话值写回磁盘。
        self._持久项目目录 = self.项目目录
        self.进程 = None
        self._输出 = queue.Queue()
        self._轮询 = None
        self._读线程 = None
        # 程序是不是正在退出。closeEvent 里靠它判断「该不该弹模态框」——
        # 退出流程中弹模态框会把事件循环卡死。
        self._正在退出 = False
        #: 收到 aboutToQuit 信号（任何人调 QApplication.quit() 都会发）
        self._收到退出信号 = False
        self._项目可见 = True
        self._对照可见 = True
        self._运行可见 = True

        self.setWindowTitle("核工坊 v%s" % 核.版本)
        self._还原窗口尺寸()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAcceptDrops(True)
        if os.path.exists(图标路径("核图标.ico")):
            self.setWindowIcon(QIcon(图标路径("核图标.ico")))

        # 自绘复选框指示器（P2-24）必须在建界面之前装好，
        # 否则设置窗口里的勾选框会先按 QSS 的纯色方块画一次。
        样式 = 安装控件样式()
        if 样式 is not None:
            样式.配色 = self.主题

        self._建界面()
        self._绑快捷键()
        self._套样式()
        self._应用窗口外观()
        self._刷新图标()
        # 配置里有字段被清洗掉了 → 启动后说一句（P1-7）。
        # 悄悄回退默认最糟：用户看到字号/主题/项目目录变了，
        # 却不知道是自己手改配置改坏了，会以为软件在乱改设置。
        # 延到事件循环起来再提示，避免在建界面途中还碰状态栏。
        坏字段 = list(getattr(配置, "上次问题", []))
        if 坏字段:
            QTimer.singleShot(0, lambda: self._提示坏配置(坏字段))

        self.装载项目树(self.项目目录)
        self.新建()
        self._刷新标题()
        # 顶行的版本控制按钮：启动时读一次 git 状态。
        # 查询走后台线程（版本查询器）—— 读 git 要起好几个子进程，
        # 同步跑会让窗口晚一秒多才显示出来，而且以后每次保存都要再等一次。
        self._版本查询 = 版本查询器(self)
        self._版本查询.好了.connect(self._版本状态好了)
        QTimer.singleShot(0, self.刷新版本状态)
        # 记住「程序层面要退了」：任何人调 QApplication.quit() 都会发这个信号。
        # closeEvent 里靠它判断「该不该弹模态框」——
        # 退出流程中弹模态框，事件循环已经在收尾，那个框永远等不到回答，
        # 整个程序就卡死退不出去。
        try:
            QApplication.instance().aboutToQuit.connect(self._标记退出中)
        except (AttributeError, RuntimeError):
            pass
        # 系统关机 / 注销：桌面会话管理器不会等我们弹确认框。
        # 默认行为是「拒绝 commitDataRequest」→ 桌面直接强杀进程，
        # 未保存的改动无声无息消失（这条以前只是推演，一直没实证）。
        # 正确做法是**接受请求**（让系统以为我们准备好了），
        # 然后在 isSavingSession() 为真的这段时间里赶紧把有改动的文档
        # 落盘 —— 用户没机会点任何按钮，能保住数据只有这一条路。
        try:
            应用 = QApplication.instance()
            应用.commitDataRequest.connect(self._会话要关机)
        except (AttributeError, RuntimeError):
            pass

    def _会话要关机(self, _管理器=None):
        """桌面要关机/注销了：把还没保存的文档尽快写盘。

        这里不弹框、不等用户 —— 会话管理器给的窗口期只有几秒，
        弹一个框必然来不及回答，反而把文件全丢掉。
        存盘失败也继续走，不能因为一个文件写不进去就卡住关机。

        **两条硬规矩**（P1-15）：

        1. 这里只做「尽快保存」，**不许永久停后台**。
           桌面是**可能取消关机**的（Windows 会问「还有程序没关，要强制关机吗」）。
           老实现存完盘直接调 收尾退出(真退出=True) → 停止(静默=True)
           + 版本查询器.停()，然后把 _正在退出 复位了事。用户点「取消」之后
           程序还在，但运行进程和版本查询器已经死了 —— 之后再点运行没反应、
           版本状态永远停在旧值，只能重启。停后台要留到真正关窗时做。
        2. **未命名文档不能静默丢**。老实现 `if not 编.文件路径: continue`
           就跳过了：用户写了一屏没保存的新文件，关个机什么都没了。
           现在先落一份恢复文件到临时目录，并在状态栏/日志里给出路径。

        真正退出（窗口销毁）时 closeEvent → 收尾退出 才会停那些东西。
        """
        self._正在退出 = True
        恢复了 = []
        try:
            for 编 in list(self.文档集):
                if not _还活着(编) or not 编.已改:
                    continue
                if 编.文件路径:
                    try:
                        self.保存(编, 弹窗=False)
                    except Exception:  # noqa: BLE001
                        continue
                    continue
                # 未命名：写一份恢复文件，别让它跟关机一起消失
                恢复 = self._写恢复文件(编)
                if 恢复:
                    恢复了.append(恢复)
            # 这里**只写配置**，不碰运行进程与版本查询器（见规矩 1）。
            self.存配置(强制=True)
            if 恢复了:
                self._记录恢复文件(恢复了)
        finally:
            # 必须复位。
            #
            # `_正在退出` 的作用是「已经问过一轮了，closeEvent 直接放行」——
            # 它只在真正关窗那一瞬间成立。而 commitDataRequest 发出来时
            # 桌面**还可能取消关机**（Windows 会问用户「还有程序没关，要强制
            # 关机吗」）。一旦用户选了取消，程序继续用，但这个标志留着 True：
            # 之后再编辑、再关窗时 closeEvent 看到它就直接 accept，
            # **关机存盘之后的新改动被静默丢弃**（实测：关机后残留 True，
            # 再关窗弹框次数 0）。
            # 所以存完盘就把标志放下来，让窗口回到「正常可关闭」状态。
            self._正在退出 = False

    def _写恢复文件(self, 编):
        """把未命名文档的当前内容写到临时目录，返回路径；失败返回 None。"""
        try:
            目录 = os.path.join(tempfile.gettempdir(), "核工坊-恢复")
            os.makedirs(目录, exist_ok=True)
            时刻 = time.strftime("%Y%m%d-%H%M%S")
            名 = "恢复_%s_%s.xht" % (时刻, getattr(编, "未命名标题", "未命名"))
            # 标题里可能有空格/序号，去掉路径非法字符
            for 字 in '<>:"/\\|?*':
                名 = 名.replace(字, "_")
            路径 = os.path.join(目录, 名)
            with open(路径, "w", encoding="utf-8", newline="\n") as f:
                f.write(编.取文本())
            return 路径
        except OSError:
            return None

    def _记录恢复文件(self, 路径们):
        """把恢复文件的路径写进日志并在状态栏提示（不能只留在内存里）。"""
        行 = "关机时未命名文档已保存到：\n" + "\n".join(路径们) + "\n"
        try:
            日志 = os.path.join(tempfile.gettempdir(), "核工坊-恢复", "恢复说明.txt")
            with open(日志, "a", encoding="utf-8") as f:
                f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + 行)
        except OSError:
            pass
        try:
            self.状态("关机：%d 个未命名文档已存到 %s" % (
                len(路径们), os.path.dirname(路径们[0])))
        except (AttributeError, RuntimeError):
            pass

    def _标记退出中(self):
        self._收到退出信号 = True

    def _提示坏配置(self, 坏字段):
        """把「哪些设置因为值不合法被重置了」告诉用户（P1-7）。"""
        明细 = "、".join("「%s」%s" % (名, 因) for 名, 因 in 坏字段[:4])
        if len(坏字段) > 4:
            明细 += " 等 %d 项" % len(坏字段)
        self.状态("配置文件有 %d 处不合法，已回退默认：%s" % (len(坏字段), 明细))
        try:
            self.状态左.setToolTip(
                "配置里有这些字段不合法，已按默认值启动（文件：%s）：\n%s"
                % (配置.配置路径(), "\n".join("· %s：%s" % (名, 因) for 名, 因 in 坏字段))
            )
        except (AttributeError, RuntimeError):
            pass

    def _还原窗口尺寸(self):
        """按上次保存的尺寸和位置还原；越界或异常就回默认值。

        `窗口尺寸` / `窗口位置` 必须先是字符串再谈内容（P1-7）：
        以前直接 `"x" in 尺寸`，配置里若写成数字，`in` 会抛
        `TypeError: argument of type 'int' is not iterable` ——
        窗口还没建完程序就退了。配置.py 已经挡过一层，这里再挡一次。
        """
        尺寸 = self.配置.get("窗口尺寸", "")
        if not isinstance(尺寸, str):
            尺寸 = ""
        宽 = 高 = None
        if "x" in 尺寸:
            try:
                部分 = 尺寸.split("x")
                宽, 高 = int(部分[0]), int(部分[1])
            except (ValueError, IndexError):
                宽 = 高 = None
        应用 = QApplication.instance()
        屏 = 应用.primaryScreen().availableGeometry() if 应用 else None
        if 宽 is None or 宽 < 900 or 高 < 600:
            宽, 高 = 1400, 880
        if 屏 is not None:
            宽 = max(min(宽, 屏.width() - 60), 900)
            高 = max(min(高, 屏.height() - 60), 620)
            # 下限不能反过来把窗口撑得比屏幕还大：小屏（1024x600 上网本、
            # 或缩放 150% 后的 1280x720）上 900/620 这两个下限会顶穿可用区，
            # 窗口底边（状态栏、运行窗输入行）落到屏幕外，点都点不到。
            宽 = min(宽, 屏.width())
            高 = min(高, 屏.height())
        self.resize(宽, 高)

        位置 = self.配置.get("窗口位置", "")
        if not isinstance(位置, str):
            位置 = ""
        if "," in 位置:
            try:
                x, y = (int(v) for v in 位置.split(","))
                # 要看**所有**显示器，不能只看主屏：副屏在主屏左边/上边时
                # 坐标是负数，主屏 contains 必然为假 —— 用户上次把窗口
                # 放在副屏，这次启动就被拽回主屏，位置记忆等于没有。
                可见 = False
                if 应用 is not None:
                    for 屏 in 应用.screens():
                        if 屏.availableGeometry().contains(x + 50, y + 30):
                            可见 = True
                            break
                if 可见:
                    self.move(x, y)
            except (ValueError, IndexError):
                pass

    # ================= 建界面 =================

    def _建界面(self):
        外框 = QWidget()
        外框.setObjectName("rootFrame")
        # 存下来：最大化时要摘掉圆角，否则屏幕四角露出桌面
        self.外框 = 外框
        外层 = QVBoxLayout(外框)
        外层.setContentsMargins(0, 0, 0, 0)
        外层.setSpacing(0)

        self.顶行 = 顶行(self)
        外层.addWidget(self.顶行)

        主体行 = QWidget()
        主体布局 = QHBoxLayout(主体行)
        主体布局.setContentsMargins(0, 0, 0, 0)
        主体布局.setSpacing(0)

        self.竖条 = 左竖条(self)
        主体布局.addWidget(self.竖条)

        self.分栏 = QSplitter(Qt.Vertical)
        self.分栏.setChildrenCollapsible(False)
        self.横栏 = QSplitter(Qt.Horizontal)
        self.横栏.setChildrenCollapsible(False)

        self.项目框 = self._建项目树()
        self.编辑框 = self._建编辑区()
        self.对照框 = self._建对照表()
        self.横栏.addWidget(self.项目框)
        self.横栏.addWidget(self.编辑框)
        self.横栏.addWidget(self.对照框)
        self.横栏.setSizes([250, 900, 280])
        self.横栏.setStretchFactor(1, 1)

        self.分栏.addWidget(self.横栏)
        self.运行框 = self._建运行窗()
        self.分栏.addWidget(self.运行框)
        self.分栏.setSizes([640, 200])
        self.分栏.setStretchFactor(0, 1)

        主体布局.addWidget(self.分栏, 1)
        外层.addWidget(主体行, 1)
        外层.addWidget(self._建状态栏())
        self.setCentralWidget(外框)
        # 无边框窗口默认没法用鼠标拖边缘改大小 —— 用户会觉得"窗口不能缩放"。
        # 打开鼠标跟踪，由 event() 在边缘交给系统原生缩放。
        self.setMouseTracking(True)
        外框.setMouseTracking(True)

    def _建项目树(self):
        框 = QWidget()
        框.setObjectName("sidePanel")
        布局 = QVBoxLayout(框)
        布局.setContentsMargins(0, 0, 0, 0)
        布局.setSpacing(0)

        头行 = QWidget()
        头行.setObjectName("panelHeader")
        头行.setFixedHeight(主题.高_面板头)
        头布局 = QHBoxLayout(头行)
        头布局.setContentsMargins(主题.内边距, 0, 主题.内边距, 0)
        头布局.setSpacing(主题.间距_紧)
        收起 = QLabel("▾")
        收起.setObjectName("crumb")
        收起.setCursor(Qt.PointingHandCursor)
        收起.setToolTip("全部收起")
        收起.mousePressEvent = lambda e: self.收起项目树()
        头布局.addWidget(收起)
        标 = QLabel("项目")
        标.setObjectName("crumb")
        头布局.addWidget(标)
        头布局.addStretch(1)
        self.项目路径标签 = QLabel("")
        self.项目路径标签.setObjectName("crumb")
        头布局.addWidget(self.项目路径标签)
        布局.addWidget(头行)

        self.树 = QTreeWidget()
        self.树.setHeaderHidden(True)
        self.树.itemDoubleClicked.connect(self._双击树)
        # **展开就加载**（P2-19）。
        # 以前只有双击文件夹时才调 _填目录，点展开箭头展开出来
        # 永远只有一个字面的「…」占位——用户看到的是「这个文件夹是空的」，
        # 或者以为树坏了。
        self.树.itemExpanded.connect(self._展开树)
        self.树.setContextMenuPolicy(Qt.CustomContextMenu)
        self.树.customContextMenuRequested.connect(self._树右键)
        布局.addWidget(self.树, 1)

        框.setMinimumWidth(180)
        return 框

    def _建编辑区(self):
        框 = QWidget()
        布局 = QVBoxLayout(框)
        布局.setContentsMargins(0, 0, 0, 0)
        布局.setSpacing(0)

        self.标签栏 = QTabBar()
        self.标签栏.setObjectName("tabBar")
        self.标签栏.setExpanding(False)
        self.标签栏.currentChanged.connect(self._切标签)
        self.标签栏.setTabsClosable(True)
        self.标签栏.tabCloseRequested.connect(self._关标签)
        # 中键点击标签关闭（与浏览器/PyCharm 一致）；右键弹菜单
        self.标签栏.setContextMenuPolicy(Qt.CustomContextMenu)
        self.标签栏.customContextMenuRequested.connect(self._标签右键)
        self.标签栏.mousePressEvent = self._标签按下
        布局.addWidget(self.标签栏)

        self.屑 = QLabel("  ")
        self.屑.setObjectName("panelHeader")
        self.屑.setFixedHeight(主题.高_状态栏)
        布局.addWidget(self.屑)

        self.容器 = QWidget()
        容器布局 = QVBoxLayout(self.容器)
        容器布局.setContentsMargins(0, 0, 0, 0)

        # 欢迎页：图标 + 标题 + 快捷键提示（对齐 PyCharm 的空编辑器页）
        self.无文档提示 = QWidget()
        欢迎 = QVBoxLayout(self.无文档提示)
        欢迎.setContentsMargins(0, 0, 0, 0)
        欢迎.setSpacing(6)
        欢迎.addStretch(1)

        图 = QLabel()
        # 和顶栏品牌标记同一条规矩：**从原图缩放**，不用预缩好的小图。
        # 实测同样缩到 84px，核图标_128.png 只剩 19.8% 的不透明像素，
        # 而从 核图标.png 原图缩是 23.2% —— 细轨道线在预缩那一步就被抹掉了，
        # 欢迎页上的标志比顶栏那个淡一截。拿不到原图时才退回 128 版。
        图标 = 缩放品牌图(84)
        if 图标 is None:
            图标 = QPixmap(图标路径("核图标_128.png"))
            if not 图标.isNull():
                图标 = 图标.scaled(84, 84, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        if 图标 is not None and not 图标.isNull():
            图.setPixmap(图标)
            图.setAlignment(Qt.AlignCenter)
            欢迎.addWidget(图)

        标题 = QLabel("核语言")
        标题.setAlignment(Qt.AlignCenter)
        # 走 objectName + 主题 QSS，不在代码里写死字号与字重：
        # 行内 setStyleSheet 不会被换主题重生成，也无法随字号设置缩放。
        标题.setObjectName("welcomeTitle")
        欢迎.addWidget(标题)

        副标 = QLabel("用中文写程序")
        副标.setAlignment(Qt.AlignCenter)
        副标.setObjectName("crumb")
        欢迎.addWidget(副标)

        欢迎.addSpacing(14)
        主提示 = QLabel("按 Ctrl+N 新建文件，或按 Ctrl+O 打开 .xht")
        主提示.setAlignment(Qt.AlignCenter)
        主提示.setObjectName("crumb")
        欢迎.addWidget(主提示)

        键 = QLabel("F5 运行      Ctrl+S 保存      Ctrl+F 查找      Ctrl+, 设置")
        键.setAlignment(Qt.AlignCenter)
        键.setObjectName("crumb")
        欢迎.addWidget(键)
        欢迎.addStretch(1)

        容器布局.addWidget(self.无文档提示)
        布局.addWidget(self.容器, 1)

        框.setMinimumWidth(320)
        return 框

    def _建对照表(self):
        框 = QWidget()
        框.setObjectName("sidePanel")
        布局 = QVBoxLayout(框)
        布局.setContentsMargins(0, 0, 0, 0)
        布局.setSpacing(0)

        头 = QWidget()
        头.setObjectName("panelHeader")
        头.setFixedHeight(主题.高_面板头)
        头布局 = QHBoxLayout(头)
        头布局.setContentsMargins(主题.内边距, 0, 主题.内边距, 0)
        头布局.setSpacing(主题.间距_紧)
        标 = QLabel("语法对照表")
        头布局.addWidget(标)
        头布局.addStretch(1)
        布局.addWidget(头)

        self.对照 = QPlainTextEdit()
        self.对照.setObjectName("refTable")
        self.对照.setReadOnly(True)
        布局.addWidget(self.对照, 1)

        框.setMinimumWidth(200)
        self._填对照表()
        return 框

    @staticmethod
    def _显示宽度(文):
        """按「屏幕占几列」算宽度：中文/全角算 2，其余算 1（P2-25）。

        `"%-10s"` 是按**字符个数**补空格的。中文名的字符数是 3、显示占 6 列，
        英文名 `print` 是 5 个字符占 5 列 —— 混在一列里 `=` 就参差不齐：
        中文行提前 3 格碰到等号，英文行准时。等宽字体下看得出来，
        这一栏本来就是为了「一眼对照」，歪着看很难受。
        """
        宽 = 0
        for 字 in 文:
            码 = ord(字)
            if (
                0x1100 <= 码 <= 0x115F          # 谚文字母
                or 0x2E80 <= 码 <= 0xA4CF      # 中日韩部首、假名、汉字
                or 0xAC00 <= 码 <= 0xD7A3      # 谚文音节
                or 0xF900 <= 码 <= 0xFAFF      # 兼容汉字
                or 0xFE30 <= 码 <= 0xFE6F      # 兼容形式
                or 0xFF00 <= 码 <= 0xFF60      # 全角
                or 0xFFE0 <= 码 <= 0xFFE6
                or 0x1F300 <= 码 <= 0x1FAFF    # emoji
            ):
                宽 += 2
            else:
                宽 += 1
        return 宽

    @classmethod
    def _补到宽(cls, 文, 宽):
        """把 文 补到**显示宽度** 宽（已经不短就原样返回）。"""
        return 文 + " " * max(0, 宽 - cls._显示宽度(文))

    def _填对照表(self):
        c = self.内核
        行 = []
        for 标题, 表, 宽 in (
            ("关键字", c.关键词表, 10),
            ("内置函数", c.函数表, 12),
            ("方法", c.方法表, 10),
            ("关键字参数", c.参数表, 8),
            ("异常类型", c.异常表, 10),
            ("标准库模块", c.模块表, 12),
            ("库成员", c.库成员表, 14),
        ):
            行.append("%s (%d)" % (标题, len(表)))
            行.append("")
            for 中, 英 in sorted(表.items()):
                行.append("  %s = %s" % (self._补到宽(中, 宽), 英))
            行.append("")
        self.对照.setPlainText("\n".join(行))

    def _建运行窗(self):
        框 = QWidget()
        布局 = QVBoxLayout(框)
        布局.setContentsMargins(0, 0, 0, 0)
        布局.setSpacing(0)

        头 = QWidget()
        头.setObjectName("runHeader")
        # 高度与另外两个面板头对齐（都走 主题.高_面板头）。
        # 以前这里写的是 30，而项目树头与对照表头是 32 —— 三个面板并排时，
        # 运行窗的标题线比另外两个高 2px，横向看过去是歪的。
        头.setFixedHeight(主题.高_面板头)
        头布局 = QHBoxLayout(头)
        头布局.setContentsMargins(主题.内边距, 0, 主题.内边距, 0)
        头布局.setSpacing(主题.间距)

        self.运行标题 = QLabel("运行")
        self.运行标题.setObjectName("runTitle")
        self.运行状态 = QLabel("就绪")
        self.运行状态.setObjectName("runStatus")
        头布局.addWidget(self.运行标题)
        头布局.addWidget(self.运行状态)
        头布局.addStretch(1)

        for 文本, 命令 in (
            ("清空", self.清空控制台),
            ("未定义清单", self.打开未定义清单),
        ):
            钮 = QLabel(文本)
            钮.setObjectName("toolBtn")
            钮.setCursor(Qt.PointingHandCursor)
            钮.mousePressEvent = lambda e, c=命令: c()
            头布局.addWidget(钮)
        布局.addWidget(头)

        self.控制台 = QPlainTextEdit()
        self.控制台.setObjectName("console")
        self.控制台.setReadOnly(True)
        self.控制台.setMaximumBlockCount(6000)
        布局.addWidget(self.控制台, 1)

        输入行 = QWidget()
        输入行.setObjectName("runHeader")
        输入行.setFixedHeight(主题.高_输入行)
        输入布局 = QHBoxLayout(输入行)
        输入布局.setContentsMargins(主题.内边距, 主题.内边距_竖, 主题.内边距, 主题.内边距_竖)
        输入布局.setSpacing(主题.间距)
        标 = QLabel("输入")
        标.setObjectName("runStatus")
        输入布局.addWidget(标)
        self.输入框 = QLineEdit()
        self.输入框.setObjectName("inputBox")
        self.输入框.setPlaceholderText("程序运行时在这里输入，回车发送")
        self.输入框.returnPressed.connect(self.发送输入)
        输入布局.addWidget(self.输入框, 1)
        布局.addWidget(输入行)

        框.setMinimumHeight(120)
        return 框

    def _建状态栏(self):
        条 = QWidget()
        条.setObjectName("statusBar")
        条.setFixedHeight(主题.高_状态栏)
        布局 = QHBoxLayout(条)
        布局.setContentsMargins(主题.内边距, 0, 主题.内边距, 0)
        布局.setSpacing(主题.间距_段)
        self.状态项目 = QLabel("")
        self.状态项目.setObjectName("statusLeft")
        # 项目名固定窄宽度，长文本只在「状态左」里滚动 —— 否则一个很深的
        # 项目路径会把中间那栏挤成 0 宽（P2-21）。
        self.状态项目.setFixedWidth(140)
        self.状态项目.setTextInteractionFlags(Qt.NoTextInteraction)
        self.状态左 = 省略标签("")
        self.状态左.setObjectName("statusLeft")
        布局.addWidget(self.状态项目)
        布局.addWidget(self.状态左, 1)
        self.状态右 = QLabel("核语言   空格 4   UTF-8")
        self.状态右.setObjectName("statusRight")
        # 右侧信息不许被挤掉：给它一个最小宽度（内容大约 260px）
        self.状态右.setMinimumWidth(260)
        布局.addWidget(self.状态右)
        return 条

    def _绑快捷键(self):
        for 键, 动作 in (
            ("F5", self.运行),
            ("Shift+F5", lambda: self.停止()),
            ("Ctrl+S", self.保存当前),
            ("Ctrl+Shift+S", self.另存为),
            ("Ctrl+N", self.新建),
            ("Ctrl+O", self.打开文件),
            ("Ctrl+P", self.快速打开),
            ("Ctrl+W", self.关闭当前),
            ("Ctrl+F", self.查找),
            ("Ctrl+G", self.跳到行),
            ("Ctrl+/", self.切换注释),
            ("Ctrl+,", self.打开设置),
            ("F9", self.检查语法),
            ("Ctrl+=", lambda: self.改字号(1)),
            ("Ctrl+-", lambda: self.改字号(-1)),
            ("Ctrl+1", self.切换项目栏),
            ("Ctrl+2", self.切换对照表),
            ("Ctrl+3", self.切换运行窗),
            ("Ctrl+Tab", lambda: self._轮换标签(1)),
            ("Ctrl+Shift+Tab", lambda: self._轮换标签(-1)),
            ("F2", self.重命名当前),
            ("Ctrl+Shift+F", self.在项目中查找),
            # 代码折叠：跟 VS Code 的 Ctrl+Shift+[ / ] 一致，好记
            ("Ctrl+Shift+[", self.折叠当前),
            ("Ctrl+Shift+]", self.展开当前),
            ("Ctrl+Shift+9", self.全部折叠),
            ("Ctrl+Shift+0", self.全部展开),
        ):
            QShortcut(QKeySequence(键), self).activated.connect(动作)

    def _轮换标签(self, 方向):
        """Ctrl+Tab 在标签间循环切换。"""
        if self.标签栏.count() < 2:
            return
        当前 = self.标签栏.currentIndex()
        新 = (当前 + 方向) % self.标签栏.count()
        self.标签栏.setCurrentIndex(新)

    @staticmethod
    def _合法文件名(新名, 扩展名=".xht"):
        """把用户输入的文件名清洗成一个**纯文件名**，不合法就返回 (None, 原因)。

        F2 重命名以前直接把输入拼进目录（P1-9）：

            ..\\逃逸.xht   → 文件被移出项目目录，标签路径变成 ...\\子\\..\\逃逸.xht
            C:\\绝对.xht   → 文件被搬到别的盘
            子/目录.xht    → os.rename 直接失败，提示「重命名失败」看不出原因
            空名           → 同上
            无后缀.xht     → 存成没有后缀的文件，项目树再也显示不出来

        规则：只接受纯文件名 —— 不含路径分隔符、不是 . / ..、不是绝对路径。
        没写后缀的自动补上（这样重命名之后项目树仍然认得它）。
        """
        名 = (新名 or "").strip('"')
        if not 名.strip():
            return None, "文件名不能为空"
        # 开头/结尾的空格要**拒绝**，不能悄悄 strip 掉（P3-2）：
        # 用户输入 `带空格 `，被静默改成 `带空格`，重命名"成功"了，
        # 但名字和他输入的不一样；结尾空格在 Windows 上更会被系统吃掉。
        if 名 != 名.strip():
            return None, "开头或结尾不能有空格"
        # 任何路径成分都拒绝：正反斜杠、盘符、以点开头的相对路径
        if any(切 in 名 for 切 in ("/", "\\")):
            return None, "文件名里不能带路径分隔符（/ 或 \\）"
        if 名 in (".", ".."):
            return None, "这不是一个文件名"
        if os.path.isabs(名) or (len(名) > 1 and 名[1] == ":"):
            return None, "不能填绝对路径"
        # 尾随的点和空格（P3-2）。
        # Windows 会在创建文件时**静默去掉**结尾的点和空格：用户输入
        # `a.`，实际得到 `a`；输入 `a ` 得到 `a`。于是「重命名成功了」，
        # 但标签上显示的名字和磁盘上的实际名字不一致，再打开就找不到原文件。
        if 名 != 名.rstrip(" ."):
            return None, "结尾不能是点或空格（Windows 会把它悄悄吃掉）"
        # Windows 设备保留名（P3-2）：CON / PRN / AUX / NUL / COM1-9 / LPT1-9。
        # 它们在**任何扩展名下**都不合法：`CON.xht` 在资源管理器里创建会失败，
        # 在部分接口下还会被当成控制台设备。os.rename 到这类名字可能报
        # 「文件名、目录名或卷标语法不正确」，提示完全看不出原因。
        主干 = 名.split(".")[0].strip().upper()
        if 主干 in ("CON", "PRN", "AUX", "NUL", "CLOCK$") or (
            len(主干) == 4 and 主干[:3] in ("COM", "LPT") and 主干[3] in "123456789"
        ):
            return None, "「%s」是 Windows 的设备保留名，不能当文件名" % 主干
        # `..foo.xht` 这种开头带点的**是**合法文件名（不是相对路径），
        # 上面已经把真正的 `.` / `..` 拦掉了，这里放行。
        # Windows 非法字符
        if any(字 in 名 for 字 in '<>:"|?*'):
            return None, "文件名里不能出现 < > : \" | ? * 这些字符"
        # 控制字符（换行、制表、NUL…）在 Windows 上一律非法。
        # 粘贴文件名时很容易带进来，不拦的话 os.rename 报的是
        # 「文件名、目录名或卷标语法不正确」，看不出到底哪儿错了。
        if any(ord(字) < 32 for 字 in 名):
            return None, "文件名里不能有换行、制表符这类控制字符"
        if not 名.lower().endswith(扩展名.lower()):
            名 += 扩展名
        # 单个文件名上限 255 个字符（NTFS 组件长度）。超了同样是系统报错，
        # 这里提前说清楚。要放在补后缀**之后**量，否则 255 个字的名字
        # 补上 .xht 就超了。
        if len(名) > 255:
            return None, "文件名太长（连后缀最多 255 个字符）"
        return 名, None

    def 重命名当前(self):
        """F2 重命名当前文件（改名后同步标签、项目树与最近打开）。"""
        if self.当前 is None or not self.当前.文件路径:
            self.状态("先保存文件再重命名")
            return
        from PySide6.QtWidgets import QInputDialog

        旧名 = os.path.basename(self.当前.文件路径)
        输入, 确定 = QInputDialog.getText(self, "重命名", "新文件名：", text=旧名)
        if not 确定 or not 输入:
            return
        新名, 原因 = self._合法文件名(输入, self.内核.扩展名)
        if 新名 is None:
            # 说清楚为什么不行，不要走到 os.rename 再报「重命名失败」
            self.状态("重命名失败：%s" % 原因)
            return
        if 新名 == 旧名:
            return
        旧路径 = self.当前.文件路径
        新路径 = os.path.join(os.path.dirname(旧路径), 新名)
        # **仅大小写不同**的重命名要放行（P3-2）。
        # Windows 文件系统不区分大小写：`a.xht → A.xht` 时
        # os.path.exists(新路径) 为真（它就是原文件自己），
        # 老代码于是报「A.xht 已经存在」，用户永远改不了大小写。
        # 判据是 normcase 之后是不是同一个路径。
        仅改大小写 = (os.path.normcase(新路径) == os.path.normcase(旧路径))
        if not 仅改大小写 and os.path.exists(新路径):
            self.状态("重命名失败：%s 已经存在" % 新名)
            return
        编 = self.当前
        try:
            if 仅改大小写:
                # 直接 rename 到同名不同大小写在 Windows 上是 no-op，
                # 必须绕一圈：先改成一个临时名，再改成目标名。
                # 第二步失败时必须改回去 —— 否则文件停在 `<旧名>.renaming`，
                # 项目树里看不到它，用户会以为文件丢了。
                临时 = 旧路径 + ".renaming"
                os.rename(旧路径, 临时)
                try:
                    os.rename(临时, 新路径)
                except OSError:
                    try:
                        os.rename(临时, 旧路径)
                    except OSError:
                        pass
                    raise
            else:
                os.rename(旧路径, 新路径)
        except OSError as e:
            self.状态("重命名失败：%s" % e)
            return
        编.文件路径 = 新路径
        # 改了名字，磁盘签名要重新取 —— 旧签名对应的是旧路径，
        # 留着它下次保存会误报「磁盘已被外部修改」。
        编._磁盘签名 = self._取磁盘签名(新路径)
        self.刷新标签(编)
        self._刷新标题()
        # 项目树与最近打开都要同步：只改标签的话，树里还是旧名字、
        # 「最近打开」点开指向旧路径（P1-9）。
        try:
            self.装载项目树(self.项目目录, 记住=False)
        except Exception:  # noqa: BLE001
            pass
        self.加最近(新路径)
        self.状态("已重命名为 %s" % 新名)

    def 在项目中查找(self):
        """Ctrl+Shift+F：在项目所有 .xht 里搜索文字，结果列在控制台。"""
        from PySide6.QtWidgets import QInputDialog

        词, 确定 = QInputDialog.getText(self, "在项目中查找", "要查找的文字：")
        if not 确定 or not 词:
            return
        命中 = 0
        跳过 = []
        self.清空控制台()
        self._写控制台("在项目中查找：%s\n" % 词)
        if not os.path.isdir(self.项目目录 or ""):
            self._写控制台("项目目录不存在：%s\n" % self.项目目录)
            self.状态("项目目录不存在，先在左侧选一个项目")
            return
        # 命中上限：控制台本身只留 6000 行，命中几万处时逐条 insertPlainText
        # 会把界面卡住好几十秒，而用户真正要看的是前几处。
        上限 = 2000
        截了 = False
        for 目录, 子目录, 文件 in os.walk(self.项目目录):
            子目录[:] = [
                d for d in 子目录
                if not d.startswith(".") and d not in ("__pycache__", "build", "dist", "版本")
            ]
            for 名 in 文件:
                if not 名.endswith(".xht"):
                    continue
                全 = os.path.join(目录, 名)
                # **用内核的编码探测，不要用 errors="replace" 假装读到了**（P1-13）。
                # 以前固定 `encoding="utf-8", errors="replace"`：
                # GBK 编码的文件里写「苹果 = 1」，读出来是乱码，搜「苹果」
                # 永远 0 命中 —— 文件明明在项目里、明明写着这两个字。
                # 内核的 读源码 已经按 UTF-8-sig → UTF-8 → GBK 探测过，
                # 和打开文件时用的是同一套口径，这里直接复用。
                try:
                    内容 = self.内核.读源码(全, 严格=True)
                except (OSError, UnicodeDecodeError):
                    # 读不了（二进制、权限、编码都猜不中）就跳过并计数，
                    # 不崩、也不把它当成「没命中」悄悄吞掉。
                    跳过.append(os.path.relpath(全, self.项目目录))
                    continue
                for 号, 行 in enumerate(内容.splitlines(), 1):
                    if 词 in 行:
                        命中 += 1
                        if 命中 <= 上限:
                            相对 = os.path.relpath(全, self.项目目录)
                            self._写控制台(
                                "%s:%d:  %s\n" % (相对, 号, 行.rstrip())
                            )
                        else:
                            截了 = True
        if 截了:
            self._写控制台("\n（命中太多，只列出前 %d 处）\n" % 上限)
        self._写控制台("\n共 %d 处\n" % 命中)
        if 跳过:
            self._写控制台("跳过 %d 个读不了的文件：%s\n"
                           % (len(跳过), "、".join(跳过[:5])))
        self.状态(
            "项目内找到 %d 处%s" % (
                命中, ("，跳过 %d 个读不了的文件" % len(跳过)) if 跳过 else ""
            )
        )

    # ================= 文档管理 =================

    def 新建(self):
        编 = 编辑器(self)
        编.已改 = False
        编.hide()
        编.未命名标题 = self._未命名标题()
        self.文档集.append(编)
        self.标签栏.addTab(编.未命名标题)
        self.标签栏.setCurrentIndex(len(self.文档集) - 1)
        self._显示文档(编)
        return 编

    def _未命名标题(self):
        """给新文档起一个不重复的名字：未命名 / 未命名 2 / 未命名 3 …

        以前固定写 "未命名"：连按三次 Ctrl+N 就有三个一模一样的标签，
        用户在标签栏里根本分不清哪个是刚写的、哪个是空的。
        （PyCharm 用的是 Untitled1/2/3，同一思路。）
        序号只在「已被占用」时递增，第一个仍是干净的「未命名」。
        """
        已用 = {self.标签栏.tabText(i) for i in range(self.标签栏.count())}
        已用 |= {self._文件名(d).lstrip("● ") for d in self.文档集 if not d.文件路径}
        if "未命名" not in 已用:
            return "未命名"
        序 = 2
        while ("未命名 %d" % 序) in 已用:
            序 += 1
        return "未命名 %d" % 序

    def _显示文档(self, 编):
        self.无文档提示.hide()
        if self.当前 is not None and self.当前 is not 编:
            self.当前.hide()
        if 编.parent() is None:
            self.容器.layout().addWidget(编)
        编.show()
        self.当前 = 编
        # 标签栏的选中态必须跟着一起挪。
        #
        # 这里是**唯一**该同步的地方：以前只有 新建() 自己补了一句
        # setCurrentIndex，而 打开() / 快速打开 / 双击项目树 / 拖放
        # 都只调本函数 —— 于是打开新文件后标签高亮停在旧标签、
        # 内容区已经是新文件（实测三连：打开甲、打开乙都停在「未命名」）。
        # 这个 bug 一直是历史欠账，因为 QTabBar 非空时 addTab 不会自动选中，
        # 而视觉上「内容对了」很容易让人忽略标签没跟上。
        if 编 in self.文档集:
            索引 = self.文档集.index(编)
            if self.标签栏.currentIndex() != 索引:
                # 直接 setCurrentIndex 会触发 currentChanged → _切标签，
                # 但那边只是再调一次 _显示文档，同一对象，幂等，不会再递归下去
                # （因为此时 当前 is 编，上面的 hide/显示都跳过）。
                self.标签栏.setCurrentIndex(索引)
        self._刷新标题()
        self.更新状态栏()
        编.setFocus()

    def _标签按下(self, 事件):
        索引 = self.标签栏.tabAt(事件.position().toPoint())
        if 事件.button() == Qt.MiddleButton and 索引 >= 0:
            self._关标签(索引)
            return
        QTabBar.mousePressEvent(self.标签栏, 事件)

    def _标签右键(self, 位置):
        索引 = self.标签栏.tabAt(位置)
        if 索引 < 0:
            return
        菜单 = QMenu(self)
        for 名, 命令 in (
            ("关闭", lambda: self._关标签(索引)),
            ("关闭其他", lambda: self._关闭其他标签(索引)),
            ("复制文件路径", lambda: self._复制路径(索引)),
            ("在文件管理器中显示", lambda: self._在管理器显示(索引)),
        ):
            # 动作挂在**菜单**上而不是主窗上：挂主窗的话菜单销毁了
            # 动作还活着，每右键一次就永久多留 4 个 QAction。
            动作 = QAction(名, 菜单)
            动作.triggered.connect(lambda _=False, c=命令: c())
            菜单.addAction(动作)
        菜单.exec(self.标签栏.mapToGlobal(位置))
        # exec() 返回后菜单没用了，交给事件循环回收（同 弹出项目菜单）。
        菜单.deleteLater()

    def _关闭其他标签(self, 保留):
        """关掉除「保留」以外的所有标签。

        逐个走 关闭文档 的「要保存吗？」三选一，任一「取消」即中止。
        以前这里先把 已改 抹成 False 再强制关闭，批量操作比单个关闭
        还危险 —— 用户改了多个文件后右键「关闭其他」，未保存的修改
        无声无息全丢。批量不能比单个更宽松。
        """
        保留文档 = self.文档集[保留] if 0 <= 保留 < len(self.文档集) else None
        for 编 in list(self.文档集):
            if 编 is not 保留文档:
                if not self.关闭文档(编):
                    return

    def _复制路径(self, 索引):
        if 0 <= 索引 < len(self.文档集):
            路径 = self.文档集[索引].文件路径
            if 路径:
                应用 = QApplication.instance()
                应用.clipboard().setText(路径)
                self.状态("路径已复制")

    def _在管理器显示(self, 索引):
        if 0 <= 索引 < len(self.文档集):
            路径 = self.文档集[索引].文件路径
            if 路径 and os.path.exists(路径):
                try:
                    subprocess.run(["explorer", "/select,", os.path.normpath(路径)])
                except OSError:
                    self.状态("打不开文件管理器")

    def _切标签(self, 索引):
        if 0 <= 索引 < len(self.文档集):
            self._显示文档(self.文档集[索引])

    def _关标签(self, 索引):
        if 0 <= 索引 < len(self.文档集):
            self.关闭文档(self.文档集[索引])

    def 刷新标签(self, 编=None):
        for i, d in enumerate(self.文档集):
            名 = self._文件名(d)
            if d.已改:
                名 = "● " + 名
            if self.标签栏.tabText(i) != 名:
                self.标签栏.setTabText(i, 名)

    def _文件名(self, 编):
        """标签上显示的名字。

        未命名文档用建出来时分配的 **编.未命名标题**（未命名 / 未命名 2 …），
        不是硬编码的「未命名」—— 否则三个新标签在刷新标题时
        又会全部变回同一个名字（刷新标签 → _文件名 → "未命名"）。
        """
        路径 = getattr(编, "文件路径", None)
        if 路径:
            return os.path.basename(路径)
        return getattr(编, "未命名标题", None) or "未命名"

    def 关闭文档(self, 编, 强制=False):
        if 编.已改 and not 强制:
            # 只有「保存」和「不保存」才允许继续；X / Esc → 取消。
            # 老写法 `if 答 == QMessageBox.Cancel: return False` 漏掉了
            # NoButton(0)，于是点标题栏 X 等于「不保存」，改动直接丢。
            答 = _问保存三选(
                self, "保存确认",
                "「%s」已修改，要保存吗？" % self._文件名(编),
            )
            if 答 == "cancel":
                return False
            if 答 == "save" and not self.保存(编):
                return False
        try:
            索引 = self.文档集.index(编)
        except ValueError:
            return False
        self.文档集.remove(编)
        self.标签栏.removeTab(索引)
        编.setParent(None)
        编.deleteLater()
        if self.当前 is 编:
            self.当前 = None
            if self.文档集:
                self._显示文档(self.文档集[min(索引, len(self.文档集) - 1)])
            else:
                self.无文档提示.show()
                self._刷新标题()
                self.更新状态栏()
        return True

    def 关闭当前(self):
        if self.当前:
            self.关闭文档(self.当前)

    # ================= 文件操作 =================

    def 打开文件(self):
        路径, _ = QFileDialog.getOpenFileName(
            self, "打开核语言文件", self.项目目录,
            "核语言源文件 (*.xht);;所有文件 (*.*)",
        )
        if 路径:
            self.打开(路径)

    def _规范路径(self, 路径):
        """比较两个路径「是不是同一个文件」用的规范形式。

        **必须 abspath + normcase 一起用**（P1-27）：
        以前只 normcase 原始字符串，于是 `D:\\项目\\a.xht` 和
        `a.xht`（或 `..\\项目\\a.xht`）被当成两个不同文件，
        同一个文件在标签栏里开出两个编辑器 —— 后存的那个把先存的覆盖掉，
        用户以为改的是「另一份」。
        Windows 不区分大小写，normcase 顺便把大小写也抹平。
        """
        try:
            return os.path.normcase(os.path.abspath(路径))
        except (TypeError, ValueError):
            return None

    def _另一个标签占了这路径(self, 路径, 排除=None):
        """这个路径是不是已经被**另一个**标签打开？是就返回那个文档。

        **另存为覆盖另一个已打开文档**是数据脱节级的问题（P1-4）：
        甲、乙两个文件都开着，把甲「另存为」到乙的路径并确认覆盖后 ——
        磁盘上乙变成了甲的内容，可乙的标签里还显示着**旧内容**、已改=False。
        用户接着在那个标签里编辑并保存，就把甲刚写进去的内容又盖掉了。
        磁盘和标签从这一刻起各说各话。所以这里直接拒绝，不静默覆盖。
        """
        目标 = self._规范路径(路径)
        if 目标 is None:
            return None
        for d in self.文档集:
            if d is 排除:
                continue
            if d.文件路径 and self._规范路径(d.文件路径) == 目标:
                return d
        return None

    @staticmethod
    def _安全制表宽(值):
        """把任意值转成合规的制表宽（1–16），转不了就用默认 4。"""
        数 = None
        if isinstance(值, bool):
            数 = None
        elif isinstance(值, int):
            数 = 值
        elif isinstance(值, float) and 值 == 值 and abs(值) != float("inf"):
            数 = int(值)
        elif isinstance(值, str):
            try:
                数 = int(值.strip())
            except (TypeError, ValueError):
                数 = None
        if 数 is None or not (1 <= 数 <= 16):
            return 4
        return 数

    @staticmethod
    def _取磁盘签名(路径):
        """磁盘上这个文件的 (mtime_ns, 大小)；拿不到（不存在/无权限）返回 None。

        **必须带 ns，也必须带 size**（P1-5）：
        只比 mtime 的话，同一秒内被外部改写就看不出来 ——
        st_mtime 是浮点秒，文件系统实际精度可能只有 1s 或 2s。
        st_mtime_ns 是纳秒整数，再加大小兜一层，日常场景足够。
        """
        try:
            状 = os.stat(路径)
        except (OSError, TypeError, ValueError):
            return None
        return (状.st_mtime_ns, 状.st_size)

    def _问覆盖外部修改(self, 编):
        """磁盘上的文件在编辑期间被别人改过了 —— 问用户怎么办（P1-5）。

        返回 "overwrite" / "saveas" / "cancel"。
        以前保存**完全不看磁盘**，直接原子写覆盖：用户在别的编辑器里
        改过同一个文件，回来一保存就把它悄悄盖掉了，没有任何提示。
        """
        框 = QMessageBox(self)
        框.setWindowTitle("磁盘上的文件已修改")
        框.setText(
            "「%s」在你编辑期间已经被别的程序改过了。\n\n"
            "  覆盖   —— 用编辑器里的内容盖掉磁盘上的\n"
            "  另存为 —— 保留磁盘上的，另存成别的文件\n"
            "  取消   —— 什么都不做" % self._文件名(编)
        )
        框.setIcon(QMessageBox.Warning)
        覆盖 = 框.addButton("覆盖", QMessageBox.AcceptRole)
        另存 = 框.addButton("另存为", QMessageBox.ActionRole)
        取消 = 框.addButton("取消", QMessageBox.RejectRole)
        框.setDefaultButton(另存)
        框.setEscapeButton(取消)
        框.exec()
        点 = 框.clickedButton()
        if 点 is 覆盖:
            return "overwrite"
        if 点 is 另存:
            return "saveas"
        return "cancel"

    def _问文件已消失(self, 编):
        """要保存的文件在磁盘上没了 —— 问用户怎么办（P1-4）。

        返回 "recreate" / "saveas" / "cancel"。

        「保存」的直觉是「写回我正在编辑的那个文件」。文件已经不在了，
        这个直觉就断了：可能是用户自己删的、可能是改名了、也可能是
        整个目录被移走。默默在原路径重建，等于把「删除」这个动作反悔掉，
        而且用户完全不知道发生过什么。
        """
        框 = QMessageBox(self)
        框.setWindowTitle("文件已不存在")
        框.setText(
            "「%s」已经不在原来的位置了（被删除、改名或移动）。\n\n"
            "  重新创建 —— 在当前路径重新写一份\n"
            "  另存为   —— 存成别的文件，原路径保持没有\n"
            "  取消     —— 什么都不做" % self._文件名(编)
        )
        框.setIcon(QMessageBox.Warning)
        重建 = 框.addButton("重新创建", QMessageBox.AcceptRole)
        另存 = 框.addButton("另存为", QMessageBox.ActionRole)
        取消 = 框.addButton("取消", QMessageBox.RejectRole)
        框.setDefaultButton(另存)
        框.setEscapeButton(取消)
        框.exec()
        点 = 框.clickedButton()
        if 点 is 重建:
            return "recreate"
        if 点 is 另存:
            return "saveas"
        return "cancel"

    def _问磁盘已变(self, 编):
        """再次打开一个**已经在标签里**的文件，但磁盘内容变了（P2-1）。

        返回 "reload" / "keep" / "cancel"。

        以前 打开() 的路径去重直接 `return 旧编辑器`：用户在外部把
        a.xht 改成「甲 = 9」，再双击 a.xht，看到的还是「甲 = 1」——
        没有提示、也不重载，用户会以为磁盘根本没变。
        """
        框 = QMessageBox(self)
        框.setWindowTitle("磁盘上的文件已修改")
        框.setText(
            "「%s」已经在编辑器里打开了，但磁盘上的内容变了。\n\n"
            "  重新加载 —— 丢掉编辑器里的改动，以磁盘为准\n"
            "  保留当前 —— 继续编辑现在的内容（保存时还会再问一次）\n"
            "  取消     —— 什么都不做" % self._文件名(编)
        )
        框.setIcon(QMessageBox.Question)
        重载 = 框.addButton("重新加载", QMessageBox.AcceptRole)
        保留 = 框.addButton("保留当前", QMessageBox.RejectRole)
        取消 = 框.addButton("取消", QMessageBox.RejectRole)
        框.setDefaultButton(重载)
        框.setEscapeButton(取消)
        框.exec()
        点 = 框.clickedButton()
        if 点 is 重载:
            return "reload"
        if 点 is 保留:
            return "keep"
        return "cancel"

    @staticmethod
    def _认行尾(内容):
        """这份文件原本用的是 CRLF 还是 LF。

        编辑器内部一律 LF（QPlainTextEdit 本来就只认 \\n），
        但**保存时要按原样写回去**。以前固定 newline="\\n"：
        在 Windows 上打开一个 CRLF 的 .xht，改一个字保存，
        整个文件的行尾全被换成 LF —— git diff 显示「每一行都改了」，
        而用户只动了一个字。本仓库的 .gitattributes 明确容忍 CRLF
        （cr-at-eol），所以这种整文件改写是实打实的噪声。
        """
        return "\r\n" if "\r\n" in 内容 else "\n"

    def _重新加载(self, 编, 路径):
        """把磁盘上的内容重新读进编辑器，并刷新磁盘签名（P2-1）。"""
        try:
            内容, 编码 = self.内核.读源码(路径, 返回编码=True)
        except OSError as e:
            self.状态("重新加载失败：%s" % e)
            return False
        编.编码 = 编码
        编.行尾 = self._认行尾(内容)
        编.置文本(内容.replace("\r\n", "\n").replace("\r", "\n"))
        编.已改 = False
        try:
            编.document().setModified(False)
        except (AttributeError, RuntimeError):
            pass
        编._磁盘签名 = self._取磁盘签名(编.文件路径)
        self.刷新标签(编)
        self.状态("已重新加载 %s" % os.path.basename(路径))
        return True

    def 打开(self, 路径):
        # 去重要在 abspath 之后比（P1-27）：相对路径与绝对路径指向
        # 同一个文件时必须只开一个标签。
        规范 = self._规范路径(路径)
        for d in self.文档集:
            if d.文件路径 and 规范 is not None and self._规范路径(d.文件路径) == 规范:
                self._显示文档(d)
                # **命中同路径标签时不能直接 return 旧对象**（P2-1）：
                # 磁盘可能已经被外部改过，直接返回等于「打开成功」但内容
                # 是旧的，用户会以为磁盘没变。先比一次磁盘签名。
                记录 = getattr(d, "_磁盘签名", None)
                现在 = self._取磁盘签名(d.文件路径)
                if 记录 is not None and 现在 is not None and 现在 != 记录:
                    答 = self._问磁盘已变(d)
                    if 答 == "reload":
                        self._重新加载(d, d.文件路径)
                    elif 答 == "cancel":
                        self.状态("保持原样（磁盘上的文件已修改）")
                    # "keep" → 保持编辑器里的内容不动
                elif 记录 is not None and 现在 is None:
                    # 文件已经被删/改名了，标签还挂着旧路径
                    self.状态("文件已不存在：%s（标签里仍是打开时的内容）"
                            % os.path.basename(d.文件路径))
                return d
        if not os.path.isfile(路径):
            self.状态("文件不存在：%s" % 路径)
            return None
        try:
            内容, 编码 = self.内核.读源码(路径, 返回编码=True)
        except OSError as e:
            self.状态("打不开文件：%s" % e)
            return None
        if "\x00" in 内容:
            self.状态("这不是文本文件：%s" % os.path.basename(路径))
            return None
        编 = 编辑器(self)
        编.文件路径 = os.path.abspath(路径)
        # 记住这个文件原本是什么编码，保存时按它写回（见 编辑器.编码）。
        编.编码 = 编码
        编.行尾 = self._认行尾(内容)
        编.置文本(内容.replace("\r\n", "\n").replace("\r", "\n"))
        编._磁盘签名 = self._取磁盘签名(编.文件路径)
        编.hide()
        self.文档集.append(编)
        self.标签栏.addTab(self._文件名(编))
        self._显示文档(编)
        self.加最近(路径)
        self.状态("已打开 %s" % os.path.basename(路径))
        return 编

    def 保存(self, 编=None, 弹窗=True):
        编 = 编 or self.当前
        if 编 is None:
            return False
        if not 编.文件路径:
            return self.另存为(编)
        # **保存前先看磁盘有没有被别人改过**（P1-5）。
        #
        # 以前这里直接开写：用户在别的编辑器里改过同一个文件，
        # 回来在核工坊里敲一个字再保存，磁盘上的那份就没了 ——
        # 没有任何提示，也没有任何痕迹。
        # 打开/上次保存时记过 (mtime_ns, 大小)，这里比一次。
        #
        # `弹窗=False` 的那几条路（关机保存、批量收尾）问不了用户，
        # 但更不能丢用户的改动，所以照写；交互保存一律先问。
        磁盘记录 = getattr(编, "_磁盘签名", None)
        现在签名 = self._取磁盘签名(编.文件路径)
        if 弹窗 and 磁盘记录 is not None:
            if 现在签名 is None:
                # 文件被**删掉或改名**了（P1-4）。
                #
                # 以前这里只比「两边签名都非 None」的情况，文件消失时
                # 现在签名=None 直接把整段比较跳过 → Ctrl+S 一声不响地
                # 在原路径上重新建出这个文件。用户以为自己保存了原本那份，
                # 其实是在给一个「已被删掉的文件」凭空复活。
                答 = self._问文件已消失(编)
                if 答 == "cancel":
                    self.状态("保存已取消（原文件已不存在）")
                    return False
                if 答 == "saveas":
                    return self.另存为(编)
                # "recreate" → 继续往下写（会在原路径重新创建）
            elif 现在签名 != 磁盘记录:
                答 = self._问覆盖外部修改(编)
                if 答 == "cancel":
                    self.状态("保存已取消（磁盘上的文件已被外部修改）")
                    return False
                if 答 == "saveas":
                    return self.另存为(编)
                # "overwrite" → 继续往下写
        try:
            目录 = os.path.dirname(编.文件路径)
            if 目录 and not os.path.isdir(目录):
                os.makedirs(目录, exist_ok=True)
            # **原子写**：先写临时文件，再 os.replace 换上去。
            #
            # 直接 open(路径, "w") 是先把原文件**清空**再写 ——
            # 写到一半崩了、断电了、或者磁盘满了，原文件就没了，
            # 用户的代码直接消失。这是所有「保存」里最要命的一条路。
            #
            # os.replace 在同一分区上是原子的：要么是旧内容，要么是新内容，
            # 不会出现「半截文件」。配置.py 早就这么改了，源文件保存是同一类问题。
            文本 = 编.取文本()
            路径 = 编.文件路径
            临时 = 路径 + ".核工坊.tmp"
            # 按文件**原本的编码**写回（0.2.7 修）。
            # 以前固定 encoding="utf-8"：打开一个 GBK 编码的 .xht、
            # 改一个字、保存，文件就被悄悄转成 UTF-8 了 ——
            # 用别的老工具（或同项目里其它按 GBK 读的脚本）再打开就是乱码。
            # 用户看到的是「我只改了一个字，怎么全乱码了」。
            编码 = getattr(编, "编码", "utf-8") or "utf-8"
            # 行尾同理：按文件**原本的行尾**写回（见 _认行尾）。
            # newline="" 关掉 Python 的自动转换，由我们自己拼。
            行尾 = getattr(编, "行尾", "\n") or "\n"
            出文 = 文本.replace("\r\n", "\n").replace("\r", "\n")
            if 行尾 != "\n":
                出文 = 出文.replace("\n", 行尾)
            try:
                with open(临时, "w", encoding=编码, newline="") as f:
                    f.write(出文)
                    f.flush()
                    os.fsync(f.fileno())
            except UnicodeEncodeError:
                # 原编码写不下新内容（比如往 GBK 文件里贴了生僻字/emoji）。
                # 这时候**不能**默默换成 UTF-8 —— 用户会以为编码没变。
                # 明确改成 UTF-8，同时把新编码记到编辑器上，
                # 并在状态栏说明，让「编码变了」这件事是可见的。
                with open(临时, "w", encoding="utf-8", newline="") as f:
                    f.write(出文)
                    f.flush()
                    os.fsync(f.fileno())
                编.编码 = "utf-8"
                self.状态("原编码 %s 存不下这些字符，已改用 UTF-8" % 编码)
            os.replace(临时, 路径)
        except OSError as e:
            # 写失败：把临时文件清掉，别在项目目录里留垃圾。
            try:
                临时 = 编.文件路径 + ".核工坊.tmp"
                if os.path.exists(临时):
                    os.remove(临时)
            except OSError:
                pass
            self.状态("保存失败：%s" % e)
            if 弹窗:
                QMessageBox.warning(self, "保存失败", str(e))
            return False
        编.已改 = False
        # 同步清掉文档的 modified 位：不清的话，下一次自动高亮/重排
        # 会让 _文本变化 以为「内容又变了」，把刚存好的文档重新标成已改。
        try:
            编.document().setModified(False)
        except (AttributeError, RuntimeError):
            pass
        # 保存完把磁盘签名刷新成「刚写下去的这一份」——
        # 不刷新的话下一次保存会把这次自己的写入误判成「外部修改」。
        编._磁盘签名 = self._取磁盘签名(编.文件路径)
        self.刷新标签(编)
        self._刷新标题()
        self.状态("已保存 %s" % os.path.basename(编.文件路径))
        # 存盘是改动的天然分界点，顺手刷一下版本状态
        self.刷新版本状态()
        return True

    def 保存当前(self):
        return self.保存(self.当前, 弹窗=True)

    def 另存为(self, 编=None):
        编 = 编 or self.当前
        if 编 is None:
            return False
        # 默认落到项目目录里，而不是只给一个裸文件名（那样文件选择框
        # 会停在进程当前目录，可能是 exe 所在处，用户找不到自己的项目）。
        建议 = os.path.join(self.项目目录, self._文件名(编))
        if not 建议.endswith(self.内核.扩展名):
            建议 += self.内核.扩展名
        路径, _ = QFileDialog.getSaveFileName(
            self, "保存核语言文件", 建议,
            "核语言源文件 (*%s);;所有文件 (*.*)" % self.内核.扩展名,
        )
        if not 路径:
            return False
        # 用户没写后缀就自动补上 —— 否则存成无后缀的文件，
        # 项目树里不显示、双击也不会被关联打开。
        if not 路径.lower().endswith(self.内核.扩展名.lower()):
            路径 += self.内核.扩展名
        路径 = os.path.abspath(路径)
        # 目标是目录时直接拦掉：继续走下去会弹「要覆盖吗」，
        # 用户点「是」之后 os.replace 到目录上抛 PermissionError，
        # 得到的是「保存失败」这种语焉不详的提示。
        if os.path.isdir(路径):
            QMessageBox.warning(
                self, "保存失败",
                "「%s」是一个文件夹，不能当文件名用。\n请换一个名字。" % 路径,
            )
            self.状态("保存失败：目标是文件夹")
            return False
        # **目标是另一个已经打开的标签 → 直接拒绝**（P1-4）。
        #
        # 甲、乙两个文件都开着，把甲「另存为」到乙的路径并确认覆盖之后：
        # 磁盘上乙变成了甲的内容，可乙的标签里还显示着**旧内容**、已改=False。
        # 用户接着在那个标签里编辑保存，就把甲刚写进去的又盖掉了 ——
        # 磁盘和标签从这一刻起各说各话，谁也不知道最终内容是哪份。
        # 覆盖是破坏性的，这里不静默处理，也不自作主张切换标签。
        占了 = self._另一个标签占了这路径(路径, 排除=编)
        if 占了 is not None:
            QMessageBox.warning(
                self, "保存失败",
                "「%s」已经在另一个标签里打开了。\n\n"
                "同时写同一个文件会让磁盘和标签对不上 ——\n"
                "请先关掉那个标签，或换一个文件名。" % os.path.basename(路径),
            )
            self.状态("保存失败：目标文件已在另一个标签打开")
            return False
        # 目标已经存在时，再确认一次。
        # 系统的「另存为」对话框一般会自己问「要不要覆盖」，但那依赖原生对话框
        # 的行为（Qt 用非原生实现时不问）。这里自己兜住底 ——
        # 覆盖是破坏性的，不该只靠对话框的实现细节。
        #
        # 比较走 abspath + normcase：Windows 不区分大小写，"a.XHT" 与 "a.xht"
        # 是同一个文件；相对路径与绝对路径也必须判成同一个。
        同一文件 = bool(编.文件路径) and (
            self._规范路径(路径) == self._规范路径(编.文件路径)
        )
        if os.path.exists(路径) and not 同一文件:
            答 = QMessageBox.question(
                self, "确认覆盖", "「%s」已经存在，要覆盖吗？" % os.path.basename(路径),
                QMessageBox.Yes | QMessageBox.No,
            )
            if 答 != QMessageBox.Yes:
                return False
        # 先把原来的归属记下来：**写失败要还原**。
        # 以前是先改 文件路径 再写，写不进去（没权限、目标被占用、盘满）
        # 时文档已经指向新路径了 —— 原文件还在磁盘上好好的，
        # 可标签、下一次 Ctrl+S、「在文件管理器中显示」全指向那个
        # 根本没写成功的新名字。一次失败的另存为不该改变文档的归属。
        旧路径 = 编.文件路径
        旧签名 = getattr(编, "_磁盘签名", None)
        旧编码 = getattr(编, "编码", "utf-8")
        编.文件路径 = 路径
        # 换了目标路径，旧的磁盘签名不再对应任何文件；
        # 清掉它，免得下一次保存拿它去比新路径、误报「外部已修改」。
        编._磁盘签名 = None
        ok = self.保存(编)
        if ok:
            self.刷新标签(编)
            self.加最近(路径)
        else:
            编.文件路径 = 旧路径
            编._磁盘签名 = 旧签名
            编.编码 = 旧编码
            self.刷新标签(编)
            self._刷新标题()
        return ok

    # ================= 项目树 =================

    def 装载项目树(self, 目录, 记住=True):
        """装载项目树。

        `记住=True`（默认）：同时更新「持久配置里的项目目录」，下次启动还用它。
        `记住=False`：只切本次会话看得见的树 —— 拖放走的这条路（P1-14）。
        开关式菜单、设置里的「选择目录」、启动时都该用默认的 True，
        因为那几处用户是明确要「换到这个项目」。
        """
        self.项目目录 = 目录
        if 记住:
            self._持久项目目录 = 目录
        self.树.clear()
        from PySide6.QtWidgets import QFileIconProvider

        提供 = QFileIconProvider()
        根 = QTreeWidgetItem(self.树, [os.path.basename(目录) or 目录])
        根.setIcon(0, 提供.icon(QFileIconProvider.Folder))
        根.setExpanded(True)
        根.setData(0, Qt.UserRole, 目录)
        self._填目录(根, 目录)
        self.项目路径标签.setText(os.path.basename(目录) or 目录)
        self.状态项目.setText(os.path.basename(目录) or 目录)
        self.存配置()
        # 换了项目目录，仓库也可能换了一个。同样延后 —— 这个方法在
        # 启动时也会被调用，同步读 git 会拖慢窗口显示。
        QTimer.singleShot(0, self.刷新版本状态)

    def _填目录(self, 节点, 目录):
        from PySide6.QtWidgets import QFileIconProvider

        提供 = QFileIconProvider()
        try:
            # scandir 返回的是**要关闭的迭代器**：sorted(os.scandir(...))
            # 用完不关，Windows 上会一直握着这个目录的句柄 ——
            # 用户随后删/改名这个文件夹会报「正在被占用」，
            # Python 也会在 GC 时抛 ResourceWarning。用 with 明确关掉。
            with os.scandir(目录) as 迭代:
                项 = sorted(迭代, key=lambda e: (not e.is_dir(), e.name.lower()))
        except OSError:
            return
        有内容 = False
        for 条 in 项:
            if 条.name.startswith(".") or 条.name in _隐藏项:
                continue
            if 条.is_dir():
                子 = QTreeWidgetItem(节点, [条.name])
                子.setIcon(0, 提供.icon(QFileIconProvider.Folder))
                子.setData(0, Qt.UserRole, 条.path)
                # 占位项要打标记：它是「还没加载」的意思，不是真的有个文件叫 …
                占 = QTreeWidgetItem(子, ["…"])
                占.setData(0, Qt.UserRole + 1, "占位")
                有内容 = True
            elif 条.name.endswith((".xht", ".py", ".txt", ".md", ".json")):
                子 = QTreeWidgetItem(节点, [条.name])
                子.setIcon(0, 提供.icon(QFileIconProvider.File))
                子.setData(0, Qt.UserRole, 条.path)
                有内容 = True
        # 空目录给一句说明。
        # 以前这里什么都不放：用户设了一个空文件夹当项目，
        # 面板就是**一片空白**——没有任何文字提示这是「空项目」
        # 还是「加载失败」。对照表有内容、运行窗有「就绪」，
        # 只有项目树空着不解释，看起来像坏了。
        if not 有内容:
            提示 = QTreeWidgetItem(节点, ["（这个文件夹里没有可显示的文件）"])
            提示.setToolTip(0, "项目树只显示 .xht / .py / .txt / .md / .json 与子文件夹")
            提示.setData(0, Qt.UserRole + 1, "占位")   # 标记：不可双击打开
            提示.setForeground(0, QBrush(QColor(self.主题["禁用文本"])))

    def _展开树(self, 项):
        """展开文件夹时按需加载子项（P2-19）。

        只在「还挂着占位」时才填 —— 反复收起/展开不该重复扫描磁盘，
        也不该把已经展开过的子项再插一遍（那会变成重复条目）。
        """
        if 项 is None:
            return
        路径 = 项.data(0, Qt.UserRole)
        if not 路径 or not os.path.isdir(路径):
            return
        if 项.childCount() == 1 and 项.child(0).data(0, Qt.UserRole + 1) == "占位":
            项.takeChild(0)
            self._填目录(项, 路径)

    def _双击树(self, 项, _列):
        # 占位提示项（空目录说明 / 懒加载的「…」）不可双击打开。
        if 项.data(0, Qt.UserRole + 1) == "占位":
            return
        路径 = 项.data(0, Qt.UserRole)
        if not 路径:
            return
        if os.path.isdir(路径):
            self._展开树(项)
            项.setExpanded(True)
        elif os.path.isfile(路径):
            self.打开(路径)

    def _树右键(self, 位置):
        项 = self.树.itemAt(位置)
        if 项 is None:
            return
        路径 = 项.data(0, Qt.UserRole)
        if not 路径:
            return
        self.树.setCurrentItem(项)
        菜单 = QMenu(self)
        if os.path.isdir(路径):
            for 名, 命令 in (
                ("设为项目文件夹", lambda: self.装载项目树(路径)),
                ("在文件管理器中打开", lambda: self._在管理器显示路径(路径)),
            ):
                动作 = QAction(名, 菜单)
                动作.triggered.connect(lambda _=False, c=命令: c())
                菜单.addAction(动作)
        else:
            for 名, 命令 in (
                ("打开", lambda: self.打开(路径)),
                ("复制路径", lambda: QApplication.instance().clipboard().setText(路径)),
                ("在文件管理器中显示", lambda: self._在管理器显示路径(路径)),
            ):
                动作 = QAction(名, 菜单)
                动作.triggered.connect(lambda _=False, c=命令: c())
                菜单.addAction(动作)
        菜单.addSeparator()
        刷新 = QAction("刷新项目树", 菜单)
        刷新.triggered.connect(lambda: self.装载项目树(self.项目目录))
        菜单.addAction(刷新)
        菜单.exec(self.树.mapToGlobal(位置))
        # 同 _标签右键：动作挂菜单、菜单用完即回收，否则每右键一次
        # 就在主窗下永久留一个 QMenu + 若干 QAction。
        菜单.deleteLater()

    def _在管理器显示路径(self, 路径):
        if not os.path.exists(路径):
            return
        try:
            if os.path.isdir(路径):
                subprocess.run(["explorer", os.path.normpath(路径)])
            else:
                subprocess.run(["explorer", "/select,", os.path.normpath(路径)])
        except OSError:
            self.状态("打不开文件管理器")

    def 收起项目树(self):
        self.树.collapseAll()
        self.状态("已收起项目树")

    def 切换项目栏(self):
        self._项目可见 = not self._项目可见
        self.项目框.setVisible(self._项目可见)
        self.状态("项目栏已%s" % ("显示" if self._项目可见 else "隐藏"))

    def 切换对照表(self):
        self._对照可见 = not self._对照可见
        self.对照框.setVisible(self._对照可见)
        self.状态("语法对照表已%s" % ("显示" if self._对照可见 else "隐藏"))

    def 切换运行窗(self):
        self._运行可见 = not self._运行可见
        self.运行框.setVisible(self._运行可见)
        self.状态("运行窗口已%s" % ("显示" if self._运行可见 else "隐藏"))

    def 切换行号(self):
        self.设行号(not self.显示行号)

    def 设行号(self, 显示):
        """显示/隐藏行号栏。设置窗口的勾选框直接调它，立刻生效。"""
        self.显示行号 = bool(显示)
        for d in self.文档集:
            d.设行号(self.显示行号)
        self.状态("行号已%s" % ("显示" if self.显示行号 else "隐藏"))
        self.存配置()

    def 切换缩进线(self):
        self.设缩进线(not self.显示缩进线)

    def 设缩进线(self, 显示):
        self.显示缩进线 = bool(显示)
        for d in self.文档集:
            d.设缩进线(self.显示缩进线)
        self.状态("缩进参考线已%s" % ("显示" if self.显示缩进线 else "隐藏"))
        self.存配置()

    def 设制表宽(self, 宽):
        # 走和读配置同一套夹取：1–16、坏值回退 4。
        # 以前是 max(1, int(宽))：没有上限，配置文件/下拉框给个 200
        # 就能把缩进推到屏幕外；int("四") 还会直接抛 ValueError。
        self.制表宽 = self._安全制表宽(宽)
        for d in self.文档集:
            d.设制表宽(self.制表宽)
        self.更新状态栏()
        self.存配置()

    def 设自动高亮(self, 开):
        self.自动高亮 = bool(开)
        for d in self.文档集:
            d.设自动高亮(self.自动高亮)
        self.存配置()

    def 应用设置(self, 保存=True):
        """把当前属性一次性推给所有已打开文档 + 立即重绘 + 写盘。

        设置窗口里每改一项都会调这里（保存=False 时不写盘，等按「应用」
        或「确定」再落盘）。这样所有开关都是**当场生效**，
        不需要关掉软件重开 —— 这正是用户报的「设置应用不能马上生效」。
        """
        for d in self.文档集:
            d.应用设置()
        self.更新状态栏()
        if 保存:
            self.存配置()

    # ================= 运行 =================

    def _内核命令(self, 文件):
        if getattr(sys, "frozen", False):
            return [sys.executable, "--内核", 文件]
        return [sys.executable, os.path.join(这里, "核.py"), 文件]

    def 运行(self):
        if self.当前 is None:
            self.状态("没有打开的文档，先新建（Ctrl+N）或打开文件（Ctrl+O）")
            return
        # 没保存过的文档不能直接运行 —— 但只弹一句状态栏提示太弱：
        # 用户按 F5 后会在状态栏看到「请先保存再运行」一闪，不知道下一步该做什么。
        # 改为直接弹出保存对话框，选好路径存盘后立刻运行，一步到位。
        if not self.当前.文件路径:
            if not self.另存为(self.当前):
                # 用户点了取消：保持原样，不运行
                self.状态("已取消运行")
                return
        if self.当前.已改:
            # 运行前必须把最新内容写盘，否则跑的是磁盘上的旧版本。
            # 这里不能静默失败：保存可能因为没有权限而失败，
            # 那样运行结果会莫名其妙地对不上编辑区。
            #
            # **必须 弹窗=True**：F5 是用户主动按的交互动作，不是关机收尾。
            # 传 False 会跳过「磁盘被外部改过 / 文件已被删除」两道询问，
            # 于是按一下 F5 就把别的程序刚写的内容悄悄盖掉、
            # 或者把用户刚删掉的文件在原路径复活 —— 和 Ctrl+S 走同一条
            # 保护路才说得通（保存() 的注释里也把 False 限定给
            # 「关机保存、批量收尾」这类问不了用户的路）。
            if not self.保存(self.当前, 弹窗=True):
                self.状态("保存未完成，已取消运行")
                return
        self.停止(静默=True)
        self.清空控制台()
        # 队列要在开新进程之前换一个新的：旧读线程可能已经在关流前读到了
        # 数据、只是还没被 _吸输出 取走，那些残留会打在新一轮运行的开头。
        换队列 = getattr(self, "_输出", None)
        self._输出 = queue.Queue()
        # 解码器也要跟着这一轮走：_再捞管道 补捞尾巴时要用**同一个**，
        # 否则读线程攥着的半个汉字和补捞到的后半个会各变成一个替换符。
        self._输出解码 = codecs.getincrementaldecoder("utf-8")("replace")
        if 换队列 is not None:
            while True:
                try:
                    换队列.get_nowait()
                except queue.Empty:
                    break
        命令 = self._内核命令(self.当前.文件路径)
        self._写控制台("> " + " ".join(命令[1:]) + "\n")

        环境 = os.environ.copy()
        环境.update(
            {"PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1", "PYTHONUTF8": "1"}
        )
        try:
            self.进程 = subprocess.Popen(
                命令,
                cwd=os.path.dirname(self.当前.文件路径) or 这里,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=环境,
                # 开发模式下（用 pythonw 跑核工坊）不加这个标志，子进程
                # python.exe 会弹一个黑色控制台窗口。打包版是 GUI 子系统
                # 不受影响。git 调用早就有这个处理，统一用同一份实现。
                creationflags=版本控制.无窗口标志(),
            )
        except OSError as e:
            self._写控制台("启动失败：%s\n" % e)
            self.进程 = None
            return
        self.运行状态.setText("运行中…")
        self._刷新运行状态样式("运行")
        self.竖条.设状态点("运行")
        self._读线程 = threading.Thread(
            target=self._读输出,
            args=(self.进程, self._输出, self._输出解码),
            daemon=True,
        )
        self._读线程.start()
        self._轮询 = QTimer(self)
        self._轮询.timeout.connect(self._检查进程)
        self._轮询.start(80)

    def _读输出(self, 进程, 队列, 解码=None):
        """把子进程的输出搬进 队列。

        队列**按参数传进来**，不是每次读 self._输出 —— 运行() 开新一轮时会
        换一个新队列，而上一轮的读线程可能还活着一瞬间。如果它按属性取，
        就会把上一轮的残留写进**新**队列，等于没清干净。
        """
        try:
            os.set_blocking(进程.stdout.fileno(), False)
        except (AttributeError, OSError, ValueError):
            pass
        空读 = 0
        # **增量解码**：read1 是按字节切的，一个汉字的 3 个字节很可能
        # 正好被 65536 的边界劈开。每块各自 decode("utf-8","replace")
        # 会把那半个字变成两个替换符 —— 输出超过 64KB 的中文程序，
        # 控制台里就会零星冒出「」。增量解码器会把半截字节留到下一块。
        解码 = 解码 if 解码 is not None else codecs.getincrementaldecoder("utf-8")("replace")
        try:
            while True:
                try:
                    块 = 进程.stdout.read1(65536)
                except (BlockingIOError, InterruptedError):
                    块 = b""
                except (OSError, ValueError):
                    break
                if 块:
                    队列.put(解码.decode(块))
                    空读 = 0
                    continue
                已结束 = 进程.poll() is not None
                if not 已结束:
                    # 进程还活着时读到空是**正常**的（它还没打印）。
                    # 这种空读绝不能计入 空读 —— 以前不分状态一律累加，
                    # 于是子进程启动慢一点（机器负载高时半秒以上）就攒出
                    # 几十次空读；等它刚退出、最后一包还在管道里没被取走
                    # 的那一瞬间，read1 仍可能返回空，"已结束 and 空读 >= 3"
                    # 当场成立直接 break，那包输出就永远丢了。
                    # 实测表现：控制台里有「[程序结束，返回 0]」，
                    # 却看不到程序自己打印的内容。
                    空读 = 0
                    time.sleep(0.03)
                    continue
                # 进程结束后才计「连续空读」，并且每次之间让出 CPU，
                # 给系统留出把管道尾包交付过来的时间。
                空读 += 1
                if 空读 >= 5:
                    break
                time.sleep(0.01)
        finally:
            # 收尾：把解码器里攒着的最后半截字节吐出来（正常 UTF-8 流里
            # 没有残留；真有的话让它变成替换符，总比悄悄丢掉强）。
            尾 = 解码.decode(b"", True)
            if 尾:
                队列.put(尾)

    def _检查进程(self):
        self._吸输出()
        if self.进程 is not None and self.进程.poll() is not None:
            码 = self.进程.returncode
            读 = getattr(self, "_读线程", None)
            if 读 is not None and 读.is_alive():
                读.join(timeout=1.0)
            # 读线程万一没能在 1 秒内排空（负载高、输出量大），这里再主动
            # 捞一次管道 —— _收尾 会把流关掉，关掉之后残留就再也拿不到了。
            # 实测过「有结束码、没有程序输出」的回归，漏的就是这一手。
            self._再捞管道()
            self._吸输出()
            self._收尾()
            self._写控制台("\n[程序结束，返回 %d]\n" % 码)
            self.运行状态.setText("就绪")
            self._刷新运行状态样式("就绪")
            self.竖条.设状态点("空闲")
            self.状态("运行结束（返回 %s）" % 码)
            if self._轮询:
                self._轮询.stop()
                self._轮询 = None

    def _再捞管道(self):
        """把 stdout 里剩下的字节直接塞进当前队列，不依赖读线程。

        只在进程已结束、准备收尾之前调用 —— 此时已无并发写入，
        读到的是读线程剩下的尾巴。
        """
        队列 = getattr(self, "_输出", None)
        进程 = self.进程
        if 队列 is None or 进程 is None:
            return
        流 = getattr(进程, "stdout", None)
        if 流 is None:
            return
        try:
            剩余 = 流.read()
        except (OSError, ValueError):
            return
        if 剩余:
            读 = getattr(self, "_读线程", None)
            共 = getattr(self, "_输出解码", None)
            if 共 is not None and (读 is None or not 读.is_alive()):
                # 读线程已经收工，可以安全接着用它的解码器：
                # 半个汉字的字节还在里面，这样拼起来才是完整的字。
                队列.put(共.decode(剩余, True))
            else:
                队列.put(剩余.decode("utf-8", "replace"))

    @staticmethod
    def _杀进程树(进程):
        """结束子进程**以及它的整棵子进程树**。

        为什么不能只用 进程.kill()：打包成 exe 之后，运行用户程序的命令是

            [核工坊Qt.exe, "--内核", 用户程序.xht"]

        也就是让 exe **自我重新调用**。PyInstaller 的单文件 exe 是
        「引导进程 + 真正跑应用的子进程」两层结构 ——
        kill() 只杀得掉引导进程，真正在跑用户代码的那个子进程会变成孤儿：
        它继续跑（死循环、无限输出），用户按了「停止」却发现程序没停，
        而且那个孤儿还**锁着 exe 文件**，导致下次打包失败。
        （测试/验exe界面.py 早就踩过同一个坑，用 taskkill /T 才解决。）

        开发模式（python.exe 跑 核.py）只有一层，kill() 就够；
        但从 exe 里运行时必须用 taskkill /T 连整棵树一起杀。
        这里统一按「打包模式优先用 taskkill，失败再退回 kill」处理。
        """
        码 = None
        if sys.platform == "win32":
            try:
                r = subprocess.run(
                    ["taskkill", "/T", "/F", "/PID", str(进程.pid)],
                    capture_output=True,
                    timeout=15,
                    creationflags=版本控制.无窗口标志(),
                )
                码 = r.returncode
            except (OSError, subprocess.SubprocessError):
                码 = None
        if 码 != 0:
            # taskkill 不可用 / 进程已经没了 / 非 Windows —— 退回普通 kill
            try:
                进程.kill()
            except OSError:
                pass

    def _刷新运行状态样式(self, 状态):
        """按运行状态给「运行中 / 就绪」那个标签换色。

        为什么统一走一个方法：以前 运行() / _检查进程() / 停止() 三处
        各自写 setStyleSheet("color: …") 和 setStyleSheet("")，
        三处的「回到就绪」写法还不完全一样。现在只在这里决定：
        · 运行中 → 主题的「强调」色（和顶栏运行按钮同一套观感）
        · 就绪   → 空样式表，回落到 #runStatus 的 __次要文本__
        只改这一个控件的行内样式，不会覆盖主题里的其它规则。
        """
        if 状态 == "运行":
            self.运行状态.setStyleSheet("color: %s;" % self.主题["强调"])
        else:
            self.运行状态.setStyleSheet("")

    def _收尾(self):
        """关掉子进程的管道，并把进程/读线程引用一起清干净。

        **必须同时清 `_读线程`**（0.2.7 修）：以前只关流、只把 进程 置 None，
        读线程对象自己还活着。下一次 运行() 会直接覆盖 self._读线程，
        旧线程从此没人管 —— 它正在 read1 上等数据，要等流被真正关闭
        才会退出来，中途空转几百毫秒到几秒。连续运行十几次就是十几个
        这样的僵尸线程在后台转，加上每次 _检查进程 里的 join(timeout=1.0)
        都会等它，停止响应明显变慢。
        """
        进程 = self.进程
        线程 = getattr(self, "_读线程", None)
        if 进程 is None:
            self._读线程 = None
            return
        for 名 in ("stdin", "stdout"):
            流 = getattr(进程, 名, None)
            if 流:
                try:
                    流.close()
                except (OSError, ValueError):
                    pass
        # 收尸：Popen 的 returncode 只有 poll()/wait() 才会填上。
        # 以前杀完直接把引用置 None，对象被回收时 subprocess 会报
        # 「subprocess NNNN is still running」的资源警告（实测跑一次
        # 界面测试就冒一条），Windows 上那个进程句柄也一直挂着没释放。
        # 走到这里的进程要么已经自然结束、要么刚被 _杀进程树 杀过，
        # 正常都是立刻返回；给 0.5 秒兜底，等不到就 poll 一下不强等。
        try:
            进程.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            try:
                进程.poll()
            except (OSError, ValueError):
                pass
        except (OSError, ValueError):
            pass
        self.进程 = None
        # 流已经关了，读线程会很快从 read1 返回并退出；短暂 join 一下，
        # 拿不到也不强等（daemon 线程，不会拖住退出）。
        if 线程 is not None and 线程.is_alive():
            try:
                线程.join(timeout=0.3)
            except RuntimeError:
                pass
        self._读线程 = None

    def 停止(self, 静默=False):
        if self.进程 is None:
            if not 静默:
                self.状态("当前没有在运行的程序")
            return
        self._杀进程树(self.进程)
        self._收尾()
        if self._轮询:
            self._轮询.stop()
            self._轮询 = None
        if not 静默:
            self._写控制台("\n[已停止]\n")
            self.运行状态.setText("就绪")
            self._刷新运行状态样式("就绪")
            self.竖条.设状态点("空闲")
            self.状态("已停止")

    def 发送输入(self):
        文 = self.输入框.text()
        self.输入框.clear()
        if self.进程 is None or self.进程.poll() is not None:
            self._写控制台("（程序已结束，这句没发出去）\n")
            return
        try:
            self.进程.stdin.write((文 + "\n").encode("utf-8"))
            self.进程.stdin.flush()
            # 回显也要走 _写控制台：程序刚打印的提示语（多半不带换行）
            # 后面就该紧接着用户输入，appendPlainText 会把它挤到下一行。
            self._写控制台(文 + "\n")
        except (OSError, ValueError) as e:
            self._写控制台("发送失败：%s\n" % e)

    def _写控制台(self, 文本):
        """把文本原样接进运行窗口，**保留它自己的换行结构**。

        以前统一用 appendPlainText(文本.rstrip("\\n"))：QPlainTextEdit 的
        appendPlainText 每次都新起一段，于是程序里不带 \\n 的输出
        （input 的提示语、核尾="" 的打印、进度提示）都被硬生生截成两行 ——
        实测 `请输入：` 和随后回显的 `小明` 明明该在同一行，却分成了两行。
        改法：直接 insertPlainText，光标先移到文末；要不要换行由文本自己决定。
        """
        if not 文本:
            return
        # 先记下「用户原来是不是停在底部附近」，再插入。
        #
        # 以前无条件 setValue(条.maximum())：用户把日志往上翻着看，
        # 每来一行输出就被拽回底部，根本没法读（实测 201/201 次都被拉回）。
        # 只有本来就贴着底部时才跟随；已经翻上去的，保持用户的位置。
        条 = self.控制台.verticalScrollBar()
        if 条 is not None:
            贴底 = 条.value() >= 条.maximum() - 4
        else:
            贴底 = True
        游 = self.控制台.textCursor()
        游.movePosition(QTextCursor.End)
        self.控制台.setTextCursor(游)
        self.控制台.insertPlainText(文本)
        if 贴底 and 条 is not None:
            条.setValue(条.maximum())

    def 清空控制台(self):
        self.控制台.clear()

    def _吸输出(self):
        while True:
            try:
                文本 = self._输出.get_nowait()
            except queue.Empty:
                return
            self._写控制台(文本)

    def 检查语法(self):
        # 语法检查编译的是编辑区里的当前文本（见下面 编译源码 的入参），
        # 根本不需要文件已保存 —— 原来那句「先保存文件再检查语法」是多余的限
        # 制，用户在未命名标签里按 F9 会被挡住。只有在需要路径做错误前缀时
        # 才用一个占位名。
        if self.当前 is None:
            self.状态("没有打开的文档")
            return
        路径 = self.当前.文件路径 or os.path.join(self.项目目录, "未命名%s" % self.内核.扩展名)
        # 未定义清单写到项目目录 —— 之前用 未定义报告(None)，
        # 而 保存() 遇到 None 路径会直接返回，于是按 F9 永远看不到记录。
        # 用 取报告 拿共享实例：运行程序那边也用它，两个实例各自
        # 「读一次、整份写回」会互相冲掉新增记录。
        报告 = self.内核.取报告(
            os.path.join(self.项目目录, self.内核.未定义文件名)
        )
        # 错误信息要送进运行窗口的控制台，不能写 sys.stderr ——
        # GUI 里 stderr 没有去处，用户按 F9 只看到状态栏一句
        # 「语法有误，见运行窗口」，却根本看不到任何报错详情。
        import io

        缓冲 = io.StringIO()
        try:
            代码, _ = self.内核.编译源码(self.当前.取文本(), 路径, 报告, 缓冲)
        finally:
            报告.保存()
        详情 = 缓冲.getvalue()
        if 代码 is None:
            self._写控制台((详情.rstrip("\n") if 详情 else "语法有误") + "\n")
            self.状态("语法有误，详情见运行窗口")
        else:
            if 详情.strip():
                self._写控制台(详情.rstrip("\n") + "\n")
            self.状态("检查通过")

    def 打开未定义清单(self):
        # 清单写在**运行的文件所在目录**（见 核.默认报告路径）。
        # 当前文档在别的目录时，先看那个目录 —— 否则用户明明在
        # 别的项目里跑过程序，这里却只显示项目目录下的那份。
        候选 = []
        if self.当前 and self.当前.文件路径:
            候选.append(
                os.path.join(
                    os.path.dirname(os.path.abspath(self.当前.文件路径)),
                    self.内核.未定义文件名,
                )
            )
        候选.append(os.path.join(self.项目目录, self.内核.未定义文件名))
        for 路径 in 候选:
            if os.path.exists(路径):
                self.打开(路径)
                return
        self.状态("还没有未定义记录")

    # ================= 帮助 =================

    def 打开说明文档(self):
        """打开项目自带的 说明.md。

        tkinter 版一直有「帮助 → 打开说明文档」，迁到 Qt 时漏了 ——
        用户手边明明有说明书，界面上却打不开。

        在**内置标签页**里打开，而不是丢给系统默认程序：
          · 不依赖 .md 的文件关联（没装 Markdown 程序的机器上会失败）；
          · 不会突然弹出记事本盖住界面；
          · 和「打开版本记录」行为一致。
        """
        路径 = self._找文档("说明.md")
        if 路径:
            self.打开(路径)
        else:
            self.状态("找不到 说明.md")

    @staticmethod
    def _找文档(名):
        """在程序目录和打包临时目录里找一份文档，找不到返回 None。"""
        for 基 in (这里, getattr(sys, "_MEIPASS", 这里)):
            if not 基:
                continue
            候选 = os.path.join(基, 名)
            if os.path.isfile(候选):
                return 候选
        return None

    def 打开版本记录(self):
        路径 = self._找文档("版本记录.md")
        if 路径:
            self.打开(路径)
        else:
            self.状态("找不到 版本记录.md")

    def 版本历史(self):
        try:
            import 帮助窗口

            旧 = getattr(self, "_版本历史", None)
            if 旧 is not None and _还活着(旧) and 旧.isVisible():
                # 已经开着就提到前面（同 查找 / 版本控制面板）：
                # 每点一次都新建一个的话，屏幕上会叠出好几个同样的窗口。
                旧.raise_()
                旧.activateWindow()
                return
            # 传项目目录：打包版的 版本/ 不在 exe 里，得去项目目录找
            self._版本历史 = 帮助窗口.版本历史对话框(
                self, 核.版本, self.项目目录
            )
            # 同上：非模态窗口必须自回收，否则版本历史每开一次漏一个。
            self._版本历史.setAttribute(Qt.WA_DeleteOnClose, True)
            self._版本历史.show()
            self._版本历史.raise_()
        except Exception as e:  # noqa: BLE001
            self.状态("打不开版本历史：%s" % e)

    def 关于(self):
        try:
            import 帮助窗口

            旧 = getattr(self, "_关于", None)
            if 旧 is not None and _还活着(旧) and 旧.isVisible():
                旧.raise_()
                旧.activateWindow()
                return
            self._关于 = 帮助窗口.关于对话框(self, 核.版本)
            # 同上：非模态窗口必须自回收，否则「关于」每开一次漏一个。
            self._关于.setAttribute(Qt.WA_DeleteOnClose, True)
            self._关于.show()
            self._关于.raise_()
        except Exception as e:  # noqa: BLE001
            self.状态("打不开关于：%s" % e)

    def 语法速查(self):
        """帮助菜单里的「语法速查」就是右侧的对照表面板 —— 不另造一份。

        原来是独立弹窗，但 Qt 版已经有常驻的对照表面板，
        再做一个只显示同样内容的窗口就是重复功能。
        """
        if not self._对照可见:
            self.切换对照表()
        else:
            self.状态("语法对照表已在右侧（Ctrl+2 可开关）")

    # ================= 视图与主题 =================

    def 切换注释(self):
        if self.当前:
            self.当前.切换注释()

    # ================= 代码折叠 =================

    def 折叠当前(self):
        """折叠光标所在的块。"""
        编 = self.当前
        if 编 is None:
            return
        块 = 编.textCursor().block()
        if not 编.可折叠(块):
            self.状态("这一行不是块的开头（块以冒号结尾）")
            return
        if not 编.已折叠(块):
            编.切换折叠(块)
        self.状态("已折叠")

    def 展开当前(self):
        """展开光标所在的块；光标在块内部时展开覆盖它的那一块。"""
        编 = self.当前
        if 编 is None:
            return
        块 = 编.textCursor().block()
        if 编.已折叠(块):
            编.切换折叠(块)
            self.状态("已展开")
            return
        # 光标在块内部：找把它盖住的那个折叠
        行 = 块.blockNumber()
        上 = 编.document().firstBlock()
        while 上.isValid():
            if 编.已折叠(上):
                止 = 编.折叠区(上)
                if 止 is not None and 上.blockNumber() < 行 <= 止:
                    编.切换折叠(上)
                    self.状态("已展开")
                    return
            上 = 上.next()
        self.状态("这一行没有被折叠")

    def 全部折叠(self):
        if self.当前:
            self.当前.全部折叠()
            self.状态("已全部折叠")

    def 全部展开(self):
        if self.当前:
            self.当前.全部展开()
            self.状态("已全部展开")

    # ================= 版本控制（只读） =================

    def 刷新版本状态(self):
        """请求读一次 git 状态并更新顶行按钮文字。

        只读 —— 不提交、不暂存、不推送。详见 版本控制.py 的模块说明。
        查询在后台线程跑（见 版本查询器）；git 不存在或不是仓库时
        降级成「未启用」，不报错，也不卡界面。
        """
        按钮 = getattr(self.顶行, "版本钮", None)
        查询器 = getattr(self, "_版本查询", None)
        if 按钮 is None or 查询器 is None:
            return
        按钮.setToolTip("正在读取版本控制状态…")
        查询器.查(self.项目目录)

    def _版本状态好了(self, 状态, 目录):
        """后台查询回来了（在主线程里执行）。"""
        if 目录 != self.项目目录:
            return  # 项目已经切走，这次结果过期了
        按钮 = getattr(self.顶行, "版本钮", None)
        if 按钮 is None:
            return
        self._版本状态 = 状态
        按钮.setText(版本控制.摘要(状态))
        原因 = 状态.get("原因") or ""
        提示 = "版本控制"
        if 状态.get("可用"):
            提示 = "分支 %s　·　%d 个文件有改动（点击查看）" % (
                状态.get("分支") or "?", len(状态.get("改动") or [])
            )
        elif 原因:
            提示 = "版本控制未启用：%s" % 原因
        按钮.setToolTip(提示)

    def 版本控制面板(self):
        try:
            import 版本控制窗口

            旧 = getattr(self, "_版本窗", None)
            if 旧 is not None and _还活着(旧) and 旧.isVisible():
                # 已经开着一个就把它提到前面，别再叠一个新的（P2-2）。
                # 以前每点一次「版本控制」都 new 一个窗口，旧的还开着，
                # 屏幕上堆出好几个一模一样的面板，_版本窗 只记得最后一个，
                # 换主题/刷新也只作用于最后那个。
                if getattr(旧, "目录", None) == self.项目目录:
                    旧.刷新()
                    旧.raise_()
                    旧.activateWindow()
                    return
                旧.close()
            self._版本窗 = 版本控制窗口.版本控制窗口(self, self.项目目录)
            # 同上：版本控制面板每开一次也漏一个隐藏 QDialog。
            self._版本窗.setAttribute(Qt.WA_DeleteOnClose, True)
            self._版本窗.show()
            self._版本窗.raise_()
        except Exception as e:  # noqa: BLE001
            self.状态("打不开版本控制面板：%s" % e)

    def 快速打开(self):
        try:
            import 快速打开

            self._快速 = 快速打开.快速打开(self)
            # exec() 是模态的，返回后这个对象就该被回收。
            # 以前只 exec 不 deleteLater，每按一次 Ctrl+P 就漏一个 QDialog。
            self._快速.exec()
            self._快速.deleteLater()
        except Exception as e:  # noqa: BLE001
            self.状态("快速打开失败：%s" % e)

    def 搜索回车(self):
        """顶行搜索框回车：在**当前文档**里找下一处。

        以前这个信号直接连的是 查找()（开面板），而 查找() 的注释却写着
        「想快速定位下一处，继续用搜索框回车（它自己连的是 查找下一个）」——
        说的和做的不是一回事：在搜索框里敲个词按回车，弹出来的是替换面板，
        想连着按回车跳下一处根本做不到。
        现在按注释里说的做：有词有文档就跳下一处，找不到给一句状态；
        词是空的（或没有打开的文档）才开面板，让用户有个输入的地方。
        """
        词 = ""
        try:
            词 = self.顶行.搜索.text().strip()
        except (AttributeError, RuntimeError):
            词 = ""
        if not 词 or self.当前 is None:
            self.查找()
            return
        if self.当前.查找下一个(词):
            self.状态("找到：%s" % 词)
        else:
            self.状态("找不到「%s」" % 词)

    def 查找(self):
        """Ctrl+F：打开查找/替换框；顶行搜索框有内容时直接沿用那个词。

        以前的行为是「搜索框有内容 → 只做一次 查找下一个 然后 return」，
        于是只要搜索框里还留着上次的词，Ctrl+F 就永远打不开替换面板 ——
        用户必须先手动清空搜索框，而这个前提没人知道。
        现在的取舍：**打开面板**，并把搜索框的词预填进「查找」栏；
        想快速定位下一处，继续用搜索框回车（它自己连的是 查找下一个）。
        """
        词 = ""
        try:
            词 = self.顶行.搜索.text().strip()
        except (AttributeError, RuntimeError):
            词 = ""
        try:
            import 查找对话框

            旧 = getattr(self, "_查找窗", None)
            if 旧 is not None and _还活着(旧) and 旧.isVisible():
                # 复用已经开着的查找框（P2-2）：Ctrl+F 连按三次以前会
                # 叠出三个查找框，每个都盯着同一个编辑器，用户不知道该用哪个。
                # 它内部本来就按 主窗.当前 取编辑器，切标签后照样正确。
                if 词 and hasattr(旧, "查找框"):
                    旧.查找框.setText(词)
                    旧.查找框.selectAll()
                旧.raise_()
                旧.activateWindow()
                if hasattr(旧, "查找框"):
                    旧.查找框.setFocus()
                return
            窗 = 查找对话框.查找对话框(self, self.当前)
            # 非模态窗口：关掉要能自己回收，否则每按一次 Ctrl+F
            # 就常驻一个隐藏 QDialog（实测 5 开 5 残留）。
            窗.setAttribute(Qt.WA_DeleteOnClose, True)
            if 词 and hasattr(窗, "查找框"):
                窗.查找框.setText(词)
                窗.查找框.selectAll()
            self._查找窗 = 窗
            窗.show()
            窗.raise_()
        except Exception as e:  # noqa: BLE001
            self.状态("打不开查找框：%s" % e)

    def 跳到行(self):
        try:
            import 查找对话框

            # exec() 之后必须回收（P2-26）。`X().exec()` 这种一行写法
            # 拿不到对象，按 Esc 关掉、或者点「取消」之后，
            # 这个 QDialog 只是隐藏并留在主窗的 children 里 ——
            # 每按一次 Ctrl+G 漏一个，长会话里越积越多。
            框 = 查找对话框.跳转对话框(self, self.当前)
            # **不要**再设 WA_DeleteOnClose：它和下面这句 deleteLater 是
            # 两套回收，撞在一起会二次删除。实测按 Esc 或点窗口右上角 ×
            # 关掉之后，C++ 对象已经被 WA_DeleteOnClose 删了，
            # 再 deleteLater 抛 RuntimeError，被外层 except 抓住，
            # 状态栏就冒出一句英文「打不开跳转框：Internal C++ object
            # (跳转对话框) already deleted」—— 明明关得好好的。
            # 模态框只需要 exec 之后这一句 deleteLater。
            框.exec()
            框.deleteLater()
        except Exception as e:  # noqa: BLE001
            self.状态("打不开跳转框：%s" % e)

    def 改字号(self, 差):
        """按增量调字号（Ctrl+滚轮、Ctrl+=/+ 与菜单用）。"""
        self.设字号(self.字号 + 差)

    def 设字号(self, 字号):
        """直接设定字号，夹到主题.字号最小~最大之间。

        范围统一从 主题 读，别再写死 min(9)/min(22) —— 用户反馈
        「可改字号范围太小」，而且三处各写一份早晚不一致。
        """
        self.字号 = 主题.夹字号(字号)
        self._应用字号()

    def _应用字号(self):
        """把字号真正应用到界面上。

        QSS 的 `font-size` **优先级高于 setFont()**：QSS 里给
        QPlainTextEdit 写死了 13px 时，编辑器里设的 QFont 点数会被完全
        覆盖 —— 实测 QFont.pointSize() 恒为 -1、fontMetrics 高度恒为 16，
        用户调字号看不出任何变化。
        所以字号必须重生成整份样式表（生成样式里用 __字号__ 占位符），
        再让编辑器同步自己的字体对象（行号栏、制表宽度都依赖它）。
        """
        self._套样式()
        for d in self.文档集:
            d.设置字体(self.字号)
        self.状态("字号 %d" % self.字号)
        self.存配置()

    def 等宽字体名(self):
        """编辑器实际会用的等宽字体（要写进 QSS，见 _应用字号 的说明）。"""
        try:
            from 编辑器 import 挑等宽字体

            return 挑等宽字体()
        except Exception:  # noqa: BLE001
            return 主题.等宽候选[-1]

    def _套样式(self):
        """按当前主题/字号重生成整份样式表。"""
        主题.换主题(self, self.主题, self.字号, self.等宽字体名())
        self._同步对话框样式()

    def _同步对话框样式(self):
        """把新样式表推给已经打开的对话框。

        查找 / 版本控制 / 帮助 / 快速打开 都是建的时候
        setStyleSheet(主窗.styleSheet()) 复制一份**快照** —— 独立窗口
        不会自动继承父窗口样式，但也因此不会跟着变。结果是：深色主题下
        开着查找框，切到浅色，查找框还是深色。
        这里遍历顶层窗口，凡是标了 跟主题 的就重设一遍；本窗口自己由
        主题.换主题 负责，跳过。
        """
        表 = self.styleSheet()
        应用 = QApplication.instance()
        if 应用 is None:
            return
        for 部 in 应用.topLevelWidgets():
            if 部 is self or not getattr(部, "跟主题", False):
                continue
            try:
                # 有 重套样式 的（版本控制面板：它还要按新色表重染 diff
                # 的字符格式，光换样式表不够）优先走它，其余只换样式表。
                重套 = getattr(部, "重套样式", None)
                if callable(重套):
                    重套()
                else:
                    部.setStyleSheet(表)
            except RuntimeError:
                continue  # 底层对象已经销毁

    def 换主题(self, 名):
        self.主题 = 主题.取主题(名, self.主题)
        self.主题名 = self.主题["名"]
        # 自绘复选框要用当前配色，换主题后必须同步（P2-24）
        样式 = 安装控件样式()
        if 样式 is not None:
            样式.配色 = self.主题
        self._套样式()
        self._应用窗口外观()
        self._刷新图标()
        for d in self.文档集:
            d.换主题()
        self._填对照表()
        self.状态("已切换到%s主题" % self.主题["名"])
        self.存配置()

    def _刷新图标(self):
        """主题变了以后，把自绘图标按新配色重画一遍。"""
        for 部件, 名 in ((getattr(self, "顶行", None), "顶行"), (getattr(self, "竖条", None), "竖条")):
            if 部件 is None:
                continue
            try:
                部件.刷新图标(self.主题)
            except (AttributeError, RuntimeError):
                pass

    def 打开设置(self):
        try:
            import 设置窗口Qt

            # 同 跳到行：exec() 完要把对话框收掉（P2-26）。
            # 设置对话框尤其要收 —— 它带着预览状态（_设置预览中），
            # 残留对象越多，越容易在退出时互相干扰。
            框 = 设置窗口Qt.设置对话框(self)
            # 同 跳到行：只留 exec 之后这一句回收，别再叠 WA_DeleteOnClose，
            # 否则关掉设置框时状态栏会冒一句英文的「already deleted」。
            框.exec()
            框.deleteLater()
        except Exception as e:  # noqa: BLE001
            self.状态("设置窗口打不开：%s" % e)

    def 状态(self, 文本):
        # 走 设全文：长文本由 省略标签 按可用宽度省略，全文进 tooltip。
        设 = getattr(self.状态左, "设全文", None)
        if 设 is not None:
            设(文本)
        else:
            self.状态左.setText(文本)

    def 更新状态栏(self):
        编 = self.当前
        if 编 is None:
            self.状态右.setText("核语言   空格 %d   UTF-8" % self.制表宽)
            return
        游 = 编.textCursor()
        行 = 游.blockNumber() + 1
        列 = 游.positionInBlock() + 1
        尾 = ""
        if 游.hasSelection():
            # 用位置相减，不要 len(selectedText())：
            # selectedText() 会把整段选中内容**复制成字符串**再求长度。
            # 全选一篇几万行的文件之后，每次光标移动（甚至只是方向键）
            # 都要复制一遍全文，界面会有明显卡顿。
            尾 = "   （已选 %d 字符）" % (游.selectionEnd() - 游.selectionStart())
        # 编码显示真实值：以前固定写 "UTF-8"，打开一个 GBK 文件时
        # 状态栏在说谎。现在取编辑器记下的原编码。
        编码 = (
            (getattr(编, "编码", "utf-8") or "utf-8")
            .replace("utf-8-sig", "UTF-8 BOM")
            .replace("utf-8", "UTF-8")
            .replace("gbk", "GBK")
            # 记事本存成「Unicode」的文件现在能正常读了（见 核.读源码），
            # 状态栏也要把它的真实编码显示出来，别一律写 UTF-8。
            .replace("utf-16", "UTF-16")
            .replace("utf-32", "UTF-32")
        )
        self.状态右.setText(
            "核语言   空格 %d   %s   %s   行 %d, 列 %d%s"
            % (self.制表宽, 编码,
               "CRLF" if getattr(编, "行尾", "\n") == "\r\n" else "LF",
               行, 列, 尾)
        )

    # ================= 菜单 =================

    @staticmethod
    def _加动作(菜单, 文本, 命令, 提示=None, 键=None):
        """往菜单里加一个动作。

        父对象必须是**菜单**而不是主窗：菜单用完就销毁，
        挂在主窗上的动作不会被回收 —— 每开一次菜单就往主窗里堆
        四十来个 QAction，反复点几次内存就 steadily 涨上去。

        `键` 只在菜单右侧显示成快捷键提示，**不参与按键分发**：

        · 不能用「拼进文字」的做法（`"运行\\tF5"`）—— 那样所有依赖
          `动作.text()` 的代码与测试都会拿到带制表符的名字，很难看。
        · 也不能用默认的 setShortcut：那会把键注册到窗口级，
          与 _绑快捷键 里的 QShortcut 撞车，同一个键触发两次
          （F5 一次起两个进程）。
        · 正确做法是 setShortcut 之后把它限定成 WidgetShortcut ——
          只有当焦点在**这个菜单**上时才可能生效，而菜单是模态弹层、
          弹出期间 QShortcut 不参与分发，两者不会同时触发。
          菜单右侧照样会把键序列画出来，用户看得到。
        """
        动作 = QAction(文本, 菜单)
        if 提示:
            动作.setToolTip(提示)
        if 键:
            动作.setShortcut(QKeySequence(键))
            动作.setShortcutContext(Qt.WidgetShortcut)
        动作.triggered.connect(lambda _=False, c=命令: c())
        return 动作

    def 弹主菜单(self, 锚):
        菜单 = self._建主菜单()
        菜单.exec(锚.mapToGlobal(锚.rect().bottomLeft()))
        # 菜单用完即弃：里面的 QAction 都以菜单为父对象，
        # 菜单一销毁，它们跟着回收，不会在主窗里越堆越多。
        菜单.deleteLater()

    def _建主菜单(self):
        """把主菜单建好并返回（不弹出）。

        单独抽出来是为了能测：`弹主菜单` 会 exec() 阻塞在模态循环里，
        测试拿不到菜单对象，也就没法断言「帮助菜单里到底有没有那几项」。
        拆开之后测试可以拿到菜单逐个检查条目。
        """
        菜单 = QMenu(self)
        文件 = 菜单.addMenu("文件")
        for 名, 命令, 键 in (
            ("新建", self.新建, "Ctrl+N"),
            ("打开…", self.打开文件, "Ctrl+O"),
            ("快速打开…", self.快速打开, "Ctrl+P"),
            ("打开文件夹…", self.选择项目目录, None),
            ("保存", self.保存当前, "Ctrl+S"),
            ("另存为…", self.另存为, "Ctrl+Shift+S"),
            # F2 早就绑好了，菜单里却一直找不到 —— 快捷键只有会背的人用得上。
            ("重命名…", self.重命名当前, "F2"),
            ("关闭标签", self.关闭当前, "Ctrl+W"),
            ("退出", self.退出, None),
        ):
            文件.addAction(self._加动作(文件, 名, 命令, 键=键))

        最近 = 文件.addMenu("最近打开")
        # 只列**磁盘上真的还在**的路径（P2-27）。
        # 配置里那份 self.最近 是跨会话累积的：临时文件被删、U 盘拔掉、
        # 项目改名之后，那里的条目就成了死链接 —— 点开只会弹「文件不存在」。
        # 这里顺手把失效项从内存里摘掉（下次 存配置 就落盘清理了），
        # 并在菜单底部给一个明确的清理入口，不用用户自己去翻配置文件。
        存活 = [p for p in self.最近 if isinstance(p, str) and os.path.isfile(p)]
        失效数 = len(self.最近) - len(存活)
        self.最近 = 存活
        for 路径 in self.最近[:10]:
            最近.addAction(
                self._加动作(最近, os.path.basename(路径), lambda p=路径: self.打开(p), 路径)
            )
        if 失效数:
            最近.addSeparator()
            清 = QAction("清理失效项（%d 条）" % 失效数, 最近)
            清.setEnabled(False)
            最近.addAction(清)
            if hasattr(self, "状态左"):
                self.状态("已从「最近打开」里清理 %d 条失效路径" % 失效数)
        if not 最近.actions():
            空 = QAction("（空）", 最近)
            空.setEnabled(False)
            最近.addAction(空)
        菜单.addSeparator()

        编 = 菜单.addMenu("编辑")
        # 快捷键提示用 QKeySequence 的标准键取，不手写字符串：
        # 「重做」在 Windows 上是 Ctrl+Y、别的平台上是 Ctrl+Shift+Z，
        # 写死哪一个都会在另一半平台上骗人。这几项本身走的是
        # QPlainTextEdit 自带的标准键，这里只负责把键面画出来。
        for 名, 命令, 标准键 in (
            ("撤销", lambda: self.当前 and self.当前.undo(), QKeySequence.Undo),
            ("重做", lambda: self.当前 and self.当前.redo(), QKeySequence.Redo),
        ):
            编.addAction(
                self._加动作(编, 名, 命令, 键=QKeySequence(标准键).toString())
            )
        编.addSeparator()
        for 名, 命令, 标准键 in (
            ("剪切", lambda: self.当前 and self.当前.cut(), QKeySequence.Cut),
            ("复制", lambda: self.当前 and self.当前.copy(), QKeySequence.Copy),
            ("粘贴", lambda: self.当前 and self.当前.paste(), QKeySequence.Paste),
            ("全选", lambda: self.当前 and self.当前.selectAll(), QKeySequence.SelectAll),
        ):
            编.addAction(
                self._加动作(编, 名, 命令, 键=QKeySequence(标准键).toString())
            )
        编.addSeparator()
        for 名, 命令, 键 in (
            ("注释 / 取消注释", self.切换注释, "Ctrl+/"),
            ("查找 / 替换…", self.查找, "Ctrl+F"),
            ("在项目中查找…", self.在项目中查找, "Ctrl+Shift+F"),
            ("转到行…", self.跳到行, "Ctrl+G"),
        ):
            编.addAction(self._加动作(编, 名, 命令, 键=键))
        菜单.addSeparator()

        码 = 菜单.addMenu("代码")
        for 名, 命令, 键 in (
            ("折叠当前块", self.折叠当前, "Ctrl+Shift+["),
            ("展开当前块", self.展开当前, "Ctrl+Shift+]"),
            ("全部折叠", self.全部折叠, "Ctrl+Shift+9"),
            ("全部展开", self.全部展开, "Ctrl+Shift+0"),
        ):
            码.addAction(self._加动作(码, 名, 命令, 键=键))
        菜单.addSeparator()

        运 = 菜单.addMenu("运行")
        for 名, 命令, 键 in (
            ("运行", self.运行, "F5"),
            ("停止", lambda: self.停止(), "Shift+F5"),
            ("检查语法", self.检查语法, "F9"),
            ("未定义清单", self.打开未定义清单, None),
        ):
            运.addAction(self._加动作(运, 名, 命令, 键=键))
        菜单.addSeparator()

        视 = 菜单.addMenu("视图")
        # 主题两项也画成勾选态：和下面几个开关同一套观感，
        # 点开菜单一眼看得出「现在是深色还是浅色」，不用先点一下再看界面。
        for 名 in ("深色", "浅色"):
            动作 = self._加动作(视, 名 + "主题", lambda n=名: self.换主题(n))
            动作.setCheckable(True)
            动作.setChecked(self.主题名 == 名)
            视.addAction(动作)
        视.addSeparator()
        # 这几项是**开关**，用可勾选动作，并在打开菜单时按真实状态回填。
        # 以前它们全是普通动作：点开菜单看不出「项目栏现在到底开没开」，
        # 只能点一下再观察界面上有没有变化 —— 而「显示行号」这种
        # 改变很细微，不盯着看根本分不出刚才那一下是开还是关。
        for 名, 命令, 状态取值 in (
            ("项目栏", self.切换项目栏, lambda: self._项目可见),
            ("语法对照表", self.切换对照表, lambda: self._对照可见),
            ("运行窗口", self.切换运行窗, lambda: self._运行可见),
            ("显示行号", self.切换行号, lambda: self.显示行号),
            ("显示缩进参考线", self.切换缩进线, lambda: self.显示缩进线),
        ):
            动作 = self._加动作(视, 名, 命令)
            动作.setCheckable(True)
            try:
                动作.setChecked(bool(状态取值()))
            except (AttributeError, RuntimeError):
                pass
            视.addAction(动作)
        视.addSeparator()
        for 名, 命令, 键 in (
            ("增大字号", lambda: self.改字号(1), "Ctrl+="),
            ("减小字号", lambda: self.改字号(-1), "Ctrl+-"),
            ("版本控制", self.版本控制面板, None),
        ):
            视.addAction(self._加动作(视, 名, 命令, 键=键))
        菜单.addSeparator()

        助 = 菜单.addMenu("帮助")
        for 名, 命令 in (
            ("语法速查", self.语法速查),
            ("打开说明文档", self.打开说明文档),
            ("版本历史", self.版本历史),
            ("打开版本记录", self.打开版本记录),
        ):
            助.addAction(self._加动作(助, 名, 命令))
        助.addSeparator()
        助.addAction(self._加动作(助, "关于核工坊", self.关于))
        菜单.addSeparator()

        菜单.addAction(self._加动作(菜单, "设置…", self.打开设置, 键="Ctrl+,"))
        return 菜单

    def 弹出项目菜单(self, 锚):
        菜单 = QMenu(self)
        菜单.addAction(self._加动作(菜单, "切换项目文件夹…", self.选择项目目录))
        菜单.addAction(
            self._加动作(菜单, "刷新项目树", lambda: self.装载项目树(self.项目目录))
        )
        菜单.exec(锚.mapToGlobal(锚.rect().bottomLeft()))
        菜单.deleteLater()

    def 选择项目目录(self):
        目录 = QFileDialog.getExistingDirectory(self, "选择项目文件夹", self.项目目录)
        if 目录:
            self.装载项目树(目录)
            self.状态("项目：%s" % 目录)

    # ================= 标题与外观 =================

    def _刷新标题(self):
        名 = self._文件名(self.当前) if self.当前 else ""
        点 = " ●" if (self.当前 and self.当前.已改) else ""
        完整 = "核工坊 v%s — %s%s" % (核.版本, 名 or "未打开文件", 点)
        # 标题没变就别碰 setWindowTitle：Windows 上这会把 IME 正在组字的
        # 拼音取消掉，飞快打字时会丢字（用户报的「每行吞字」）。
        改标题 = getattr(self, "_标题缓存", None) != 完整
        if 改标题:
            self._标题缓存 = 完整
            self.setWindowTitle(完整)
        self.顶行.设项目名(os.path.basename(self.项目目录) or "核语言")
        if self.当前 and self.当前.文件路径:
            父 = os.path.basename(os.path.dirname(self.当前.文件路径))
            self.屑.setText("  %s › %s" % (父, 名))
        else:
            self.屑.setText("  ")

    def _看起来最大化(self):
        """是否处于最大化/全屏。

        用 isMaximized() 而不是比对几何：无边框窗口在 Windows 上
        geometry() 往往比 availableGeometry() 少一圈（DWM 边框被裁掉），
        两者永远不相等，导致状态永远判成「未最大化」（实测圆角偏好
        被写反：最大化时写成 DO NOT ROUND 的反面）。
        """
        return bool(self.isMaximized() or self.isFullScreen())

    def _应用窗口外观(self):
        """深色标题栏 + 圆角。最大化时要反向操作，否则屏幕四角露桌面。

        现象：用户报「全屏没占满」。实测窗口矩形已经精确等于屏幕可用区
        （误差 0 像素），缺的就是四个角 —— #rootFrame 的 border-radius 12px
        在最大化时仍然生效，加上 DWM 的圆角偏好，四角被切掉，
        露出后面的桌面/阴影，看起来就像窗口小了一圈。

        注意：changeEvent(WindowStateChange) 触发时 Qt 内部的窗口状态
        可能还没完全切换，直接读 isMaximized() 会拿到旧值
        （实测在最大化事件里读到 True，属性却仍被写成 false）。
        所以这里用「窗口几何是否等于屏幕可用区」来判定，
        这个值在事件到达时已经是新的。
        """
        最大化 = self._看起来最大化()
        if getattr(self, "外框", None) is not None:
            # 最大化：圆角归零；还原：恢复 12px。交给 QSS 属性选择器，
            # 不用手写 setStyleSheet（那会把整个主题样式覆盖掉）。
            #
            # 属性名必须避开 QWidget 的内建属性：一开始用 "maximized"，
            # setProperty 被静默忽略（读回来永远是 False、
            # dynamicPropertyNames 里也没有），QSS 规则从未匹配过。
            # 换成 "窗态" 这种自造名字才存得住。
            新值 = "最大化" if 最大化 else "已还原"
            if self.外框.property("窗态") != 新值:
                self.外框.setProperty("窗态", 新值)
                self.外框.style().unpolish(self.外框)
                self.外框.style().polish(self.外框)
                self.外框.update()
        try:
            import ctypes

            dwm = ctypes.WinDLL("dwmapi", use_last_error=True)
            句柄 = int(self.winId())
            深 = ctypes.c_int(1 if self.主题名 == "深色" else 0)
            dwm.DwmSetWindowAttribute(句柄, 20, ctypes.byref(深), ctypes.sizeof(深))
            # 33 = DWMWA_WINDOW_CORNER_PREFERENCE；2 = DWMWCP_ROUND
            # 最大化时必须给 1（DWMWCP_DONOTROUND），否则四个角依旧被切。
            圆 = ctypes.c_int(1 if 最大化 else 2)
            dwm.DwmSetWindowAttribute(句柄, 33, ctypes.byref(圆), ctypes.sizeof(圆))
        except Exception:
            pass

    def changeEvent(self, 事件):
        """最大化/还原时重算圆角与 DWM 圆角偏好。

        `_应用窗口外观()` 连调两次：
          · 第一次立即调 —— DWM 属性对窗口状态最敏感，必须当场改，
            否则会看到「先圆角、后跳成直角」的闪一下；
          · 第二次用 QTimer.singleShot(0) 排到事件队列末尾 ——
            此时 Qt 的窗口状态才算真正切换完，
            属性选择器（QSS 圆角）必须在这之后才能拿到正确值。
        """
        super().changeEvent(事件)
        from PySide6.QtCore import QEvent, QTimer

        if 事件.type() == QEvent.WindowStateChange:
            self._应用窗口外观()
            QTimer.singleShot(0, self._应用窗口外观)
            # 顶栏「最大化/还原」字形跟着真实窗态走：Win+↑、贴边吸附、
            # 任务栏还原这些路径不经过 顶行.切最大化，不回填就会一直画着 □。
            try:
                self.顶行.同步窗口钮()
                QTimer.singleShot(0, self.顶行.同步窗口钮)
            except (AttributeError, RuntimeError):
                pass

    # —— 无边框窗口的边缘缩放 ——

    #: 边缘判定宽度（逻辑像素）。太窄不好抓，太宽会误伤内容区。
    边缘距 = 6

    def _落在边缘(self, 全局点):
        """这个全局坐标落在窗口的哪条边/角上（不在边缘返回 None）。"""
        if self.isMaximized() or self.isFullScreen():
            return None
        局 = self.mapFromGlobal(全局点)
        x, y = 局.x(), 局.y()
        宽, 高 = self.width(), self.height()
        距 = self.边缘距
        if not (-距 <= x <= 宽 + 距 and -距 <= y <= 高 + 距):
            return None
        左, 右 = x < 距, x > 宽 - 距
        上, 下 = y < 距, y > 高 - 距
        边 = Qt.Edges()
        if 左:
            边 |= Qt.LeftEdge
        elif 右:
            边 |= Qt.RightEdge
        if 上:
            边 |= Qt.TopEdge
        elif 下:
            边 |= Qt.BottomEdge
        return 边 or None

    @staticmethod
    def _边缘光标(边):
        """边缘对应的缩放光标，让用户看得出来这里能拖。"""
        if 边 is None:
            return None
        左右 = bool(边 & (Qt.LeftEdge | Qt.RightEdge))
        上下 = bool(边 & (Qt.TopEdge | Qt.BottomEdge))
        if 左右 and 上下:
            # 左上/右下 用主对角线，右上/左下 用副对角线
            主对角 = bool(边 & Qt.LeftEdge) == bool(边 & Qt.TopEdge)
            return Qt.SizeFDiagCursor if 主对角 else Qt.SizeBDiagCursor
        if 左右:
            return Qt.SizeHorCursor
        return Qt.SizeVerCursor

    def event(self, 事件):
        """把边缘按下交给系统做原生缩放。

        无边框窗口（FramelessWindowHint）默认既不能拖边改大小、
        也没有系统的缩放光标 —— 用户会觉得「窗口尺寸锁死了」。
        这里在边缘按下时调用 startSystemResize，交给 Windows 自己处理，
        缩放体验和普通窗口完全一致（含贴边分屏）。
        """
        from PySide6.QtCore import QEvent

        if 事件.type() == QEvent.MouseButtonPress and 事件.button() == Qt.LeftButton:
            边 = self._落在边缘(事件.globalPosition().toPoint())
            if 边 is not None:
                句柄 = self.windowHandle()
                if 句柄 is not None and 句柄.startSystemResize(边):
                    return True
        return super().event(事件)

    def mouseMoveEvent(self, 事件):
        """鼠标靠近边缘时换成缩放光标。

        只有真正能拖的时候光标才会变 —— 否则用户根本不知道无边框窗口
        还能改大小（系统不会替 FramelessWindowHint 做这件事）。
        """
        边 = self._落在边缘(事件.globalPosition().toPoint())
        光标 = self._边缘光标(边)
        if 光标 is not None:
            self.setCursor(光标)
        else:
            self.unsetCursor()
        super().mouseMoveEvent(事件)

    def 存配置(self, 强制=False):
        """把界面状态写盘，下次启动还原。

        **设置窗口预览期间不写盘**（P1-6）。
        设字号 / 设制表宽 / 设行号 / 设缩进线 / 设自动高亮 每个都会调到这里，
        而它们正是设置窗口里每动一下就调的预览入口：拖动字号滑条一次
        就写一次盘。等用户按「取消」，磁盘上早已是一串预览过的值 ——
        程序崩一次、或者还原逻辑漏了某一项，设置就被永久改掉了。
        现在预览只改内存，落盘统一在 应用 / 确定 / 取消 里做（那时它们
        会先把 _设置预览中 复位）。
        """
        if getattr(self, "_设置预览中", False) and not 强制:
            return
        self.配置.update({
            "主题": self.主题名,
            "字号": self.字号,
            "制表宽": self.制表宽,
            "缩进线": self.显示缩进线,
            "行号": self.显示行号,
            "自动高亮": self.自动高亮,
            "最近": self.最近[:12],
            # **写持久值，不写会话值**（P1-14）。
            # 拖一个文件夹进来只是想看看，self.项目目录 变成了它，
            # 但「下次启动打开哪个项目」不该因此改变。以前这里写
            # self.项目目录，于是下一次 存配置（退出、改字号、应用设置）
            # 就把临时拖进来的目录永久写死了 —— 用户完全没被告知。
            "项目目录": getattr(self, "_持久项目目录", self.项目目录),
            "窗口尺寸": "%dx%d" % (self.width(), self.height()),
            "窗口位置": "%d,%d" % (self.x(), self.y()),
        })
        配置.存配置(self.配置)

    def 加最近(self, 路径):
        路径 = os.path.abspath(路径)
        self.最近 = [p for p in self.最近 if os.path.normcase(p) != os.path.normcase(路径)]
        self.最近.insert(0, 路径)
        self.最近 = self.最近[:12]

    def 退出(self):
        """顶栏 ✕ 按钮走的路径：先问要不要保存，再关窗口。

        **不要在这里自己 quit()** —— 只要调 self.close()，
        Qt 会走 closeEvent，而 closeEvent 里已经包含了
        「确认 → 收尾 → 关闭」的完整逻辑。
        以前两个都做：先弹一遍模态框问保存，再 quit()，
        而 quit() 又会触发 closeEvent 再问一遍 —— 用户会被问两次；
        更糟的是第一次用的是模态框，在退出流程里会卡死。
        现在统一只走一条路：close() → closeEvent。
        """
        self.close()

    def _收尾退出(self, 真退出=True):
        """停子进程、停后台线程、写配置。

        `真退出=False` 用于「先把窗口 accept 掉、再问要不要保存」的那一步：
        那时用户可能点「取消」把窗口拉回来继续用，所以**只写配置，
        不碰任何还活着的后台东西** —— 一旦停了就再也起不回来了。
        """
        if 真退出:
            self.停止(静默=True)
            查询器 = getattr(self, "_版本查询", None)
            if 查询器 is not None:
                # 等后台的 git 查询收尾再退出，免得工作线程在解释器拆栈时
                # 还回来调 _完成（那时窗口对象可能已经先没了）。
                查询器.停()
        self.存配置()

    def closeEvent(self, 事件):
        """关窗口（Alt+F4、任务栏右键关闭、系统关机）也要先问要不要保存。

        这里以前**根本没有 closeEvent**：顶栏那个「✕」按钮走的是 退出()，
        有保存确认；但用户按 Alt+F4、点任务栏的关闭、或者系统要关机时，
        Qt 直接把窗口关掉 —— 未保存的修改无声无息全丢。
        实测：编辑器里改了内容、标了「已改」，再调 窗.close()，
        弹都不弹，窗口就没了。

        **两条硬规矩**（都是实测踩出来的）：

        1. 绝不能在这里弹**模态**对话框（QMessageBox.question 是模态的）。
           程序自己调 应用.quit() 时，Qt 会**同步**派发
           QEvent.WindowCloseRequest 给顶层窗口 —— 也就是走到这里。
           实测顺序（offscreen 下打点确认）：
               quit() 开始 → closeEvent → aboutToQuit → quit() 返回
           closeEvent 跑在 aboutToQuit **之前**，那时 closingDown() 还是
           False、aboutToQuit 也还没发 —— 没有任何标志能区分
           「用户按了 Alt+F4」和「程序自己在退」。而在退出流程里弹模态框，
           那个框永远等不到回答：程序就**卡死在那里退不出去**。
           实测：改完代码直接 QApplication.quit()，程序停在
           「要保存吗？」上不动，事件循环再也不退出。
           所以一律用**非模态**的确认框（QMessageBox.open()）。

        2. 绝不能 事件.ignore()。程序 quit() 时，closeEvent 里 ignore() 会
           **把整个退出流程卡住** —— 实测（最小复现：closeEvent 里只写
           事件.ignore()）应用.quit() 之后事件循环再也不返回。
           Qt 把 quit() 实现成「给所有顶层窗口发关闭请求」，
           任何一个窗口拒绝关闭，退出就停在那里。
           安全的做法：先 accept() 让窗口关掉，**然后**再弹非模态框；
           用户点「取消」就把窗口重新 show() 回来。
        """
        # 已经问过一轮了（_真正关窗 里置的位）→ 直接放行，别再盘问一遍。
        # 不认这个标志的话，用户点「不保存」之后 _真正关窗 的 close()
        # 会再触发一次本函数，把刚问完的文档**又弹一遍**。
        if getattr(self, "_正在退出", False):
            self._收尾退出()
            事件.accept()
            return

        # 没有未保存的改动 → 直接关，不用打扰用户
        if not any(编.已改 for 编 in self.文档集):
            self._收尾退出()
            事件.accept()
            return

        # 有未保存的改动 → 先让窗口关掉（accept），再弹非模态框问。
        # 不能 ignore()：那会把程序自己的 quit() 也卡住。
        # ⚠️ 这里**不能**调 查询器.停()：用户随时可能点「取消」把窗口拉回来，
        # 那时版本状态就再也不刷新了（实测「取消」后 查() 被 _停 挡掉，
        # 顶行版本号与保存后的刷新全部失效）。真正停线程放到 _真正关窗。
        事件.accept()
        # 关之前先把窗口状态拍下来：用户随时可能点「取消」，
        # 那时要按原样还原（P3-3）。必须在这里拍 —— accept() 之后
        # isMaximized() 就不可靠了。
        self._关窗窗口状态 = (
            "fullscreen" if self.isFullScreen()
            else "maximized" if self.isMaximized()
            else "normal"
        )
        self._收尾退出(真退出=False)
        if getattr(self, "_关窗确认中", False):
            return          # 已经在问了，别再弹第二个
        self._关窗确认中 = True
        # 一次性拍下「这一轮要问哪些文档」。
        #
        # 不能每轮都重新扫 self.文档集：点「不保存」只是放弃内存里的改动，
        # 文档本身还留着（用户可能点「取消」把窗口拉回来继续编辑），
        # 它的 已改 仍是 True —— 于是下一轮又把同一个文档问一遍，
        # 无限重弹，用户永远退不出去。实测连弹 6 次同一个框。
        # 拍成快照之后，每个文档在这一轮里只问一次，答完就出队。
        self._关窗待问 = [d for d in self.文档集 if _还活着(d) and d.已改]
        self._问要不要保存()

    def _问要不要保存(self):
        """非模态地问「要不要保存」，答完再决定关不关。

        为什么不用 QMessageBox.question：那是模态的，会开自己的事件循环。
        在 closeEvent 里调它会和外层的退出流程抢事件循环 —— 程序卡死。
        这里用 QMessageBox 实例 + open()（非模态），完事再关掉。

        用户选「取消」时把窗口重新显示出来 —— 刚才为了不卡住退出流程
        已经 accept() 让它关上了。
        """
        # 从 closeEvent 拍下的快照里取下一份要问的。
        # 快照本身每轮都在出队（见 选好了），所以同一个文档只会被问一次 ——
        # 这是「点不保存后无限重弹」的根治点。
        # 顺便判活：用户在确认框开着时关掉了某份文档，它的包装对象
        # 已经被 deleteLater 销毁，读 已改 会抛 RuntimeError。
        待处理 = [d for d in getattr(self, "_关窗待问", []) if _还活着(d)]
        self._关窗待问 = 待处理
        if not 待处理:
            self._关窗待问 = []
            self._关窗确认中 = False
            self._真正关窗()
            return

        编 = 待处理[0]
        框 = QMessageBox(self)
        框.setWindowTitle("未保存的修改")
        框.setText("「%s」还没保存，要保存吗？" % self._文件名(编))
        框.setIcon(QMessageBox.Question)
        框.setStandardButtons(QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        框.setDefaultButton(QMessageBox.Save)
        # Esc 必须落到「取消」。不设的话，平台默认可能是「不保存」——
        # 用户按 Esc 想反悔，结果改动被丢掉。
        框.setEscapeButton(QMessageBox.Cancel)
        框.button(QMessageBox.Save).setText("保存")
        框.button(QMessageBox.Discard).setText("不保存")
        框.button(QMessageBox.Cancel).setText("取消")

        def 拉回来():
            """用户反悔了 —— 把窗口重新显示出来，**并恢复原来的窗口状态**。

            以前固定 showNormal()：关窗前窗口是最大化（甚至全屏）的，
            点「取消」之后变成一个普通大小的窗口，布局、滚动位置、
            面板宽度全都变了样 —— 用户只是不想关，不是想把窗口缩小（P3-3）。
            状态在 closeEvent 里就拍下来了（_关窗窗口状态），这里照着还原。
            """
            状态 = getattr(self, "_关窗窗口状态", "normal")
            if 状态 == "fullscreen":
                self.showFullScreen()
            elif 状态 == "maximized":
                self.showMaximized()
            else:
                self.showNormal()
            self.raise_()
            self.activateWindow()

        def 选好了(答):
            # 这个回调是**异步**的：确认框开着的期间用户完全可以继续操作主窗口 ——
            # 关掉别的标签、把这一份删掉、甚至换项目目录。
            # 实测：确认框开着时把这份文档关掉，再点「保存」，
            # 编 背后的 C++ 对象已被 deleteLater 销毁，取文本时抛出
            #   RuntimeError: libshiboken: Internal C++ object (编辑器) already deleted
            # 而且异常打断流程、_关窗确认中 卡在 True ——
            # 之后每次关窗 accept 完就直接 return，**不再弹框**，改动静默丢失。
            # 所以：入口先判活，复位一律放 finally。
            交班 = False
            框.deleteLater()
            try:
                # X / Esc 会让 finished 拿到 NoButton(0)。必须按「取消」处理：
                # 老写法只判 `答 == QMessageBox.Cancel`，0 不等于 Cancel，
                # 于是落进下面「这一份问过了」的分支 —— 窗口关掉、改动丢失。
                判定 = _判定保存答复(答)
                if 判定 == "cancel":
                    拉回来()
                    return
                if _还活着(编) and 判定 == "save" and not self.保存(编):
                    拉回来()
                    return
                # 这一份问过了（保存了 / 放弃了 / 它已经不在了）→ 出队，
                # 然后接着问剩下那些文档。
                #
                # **必须延迟到下一轮事件循环**，不能在这里直接递归调 ——
                # 这里还在那个确认框自己的事件循环里，直接再 open() 一个框
                # 会形成嵌套的模态/非模态循环，退出流程就卡在里面出不来。
                # 实测（冒烟测试）就是这样挂死的：栈上是
                #   收 → closeEvent → _问要不要保存 → 选好了 → _问要不要保存
                交班 = True
                # 已经处理过这一份了，从待问清单里摘掉 —— 不摘的话下一轮
                # 又会把它当成「还没问」的文档，点「不保存」后无限重弹。
                self._关窗待问 = [d for d in getattr(self, "_关窗待问", []) if d is not 编]
                QTimer.singleShot(0, self._问要不要保存)
            finally:
                # 没交班就说明这一轮结束了（取消 / 保存失败拉回来 / 抛异常），
                # 守卫必须松开 —— 松不开守卫会让下次关窗静默丢改动。
                # 交班那条腿的下一轮由 _问要不要保存 自己维护标志，这里别碰。
                if not 交班:
                    self._关窗确认中 = False

        框.finished.connect(选好了)
        框.open()
        self._关窗框 = 框

    def _真正关窗(self):
        """确认完了：收尾并关掉窗口。

        ⚠️ `_正在退出` 必须先置位**再** close()：close() 会同步回调
        closeEvent，而 closeEvent 看到还有「已改」的文档就会再问一轮 ——
        点「不保存」的文档内存里仍是 已改=True，于是刚问完的窗口
        又弹一次。实测：单份文档点「不保存」弹 2 次，三份文档弹 8 次。
        closeEvent 开头靠这个标志直接放行，不再重复盘问。
        """
        self._收尾退出()
        self._正在退出 = True
        self.close()

    # ================= 拖放 =================

    def dragEnterEvent(self, 事件):
        if 事件.mimeData().hasUrls():
            # 记下当前窗态：万一拖放过程中窗口被最小化，落下时要按原样恢复
            self._拖放前窗态 = (
                "fullscreen" if self.isFullScreen()
                else "maximized" if self.isMaximized()
                else "normal"
            )
            事件.acceptProposedAction()

    def dropEvent(self, 事件):
        """拖入文件或文件夹。

        拖入**文件夹**时只切项目树，不静默写死到配置里（0.2.7 调整）：
        以前 装载项目树() 末尾无条件 存配置()，于是「顺手拖个文件夹进来看看」
        就永久改掉了下次启动的项目目录，用户完全没被告知。
        现在拖入的目录只对本次会话生效；要永久记住，
        通过「打开文件夹…」菜单或设置里显式选择（那两条路本来就有明确意图）。
        """
        切了项目 = False
        for url in 事件.mimeData().urls():
            路径 = url.toLocalFile()
            if os.path.isdir(路径):
                self._装载项目树不存配置(路径)
                切了项目 = True
            elif 路径.lower().endswith(".xht"):
                self.打开(路径)
        事件.acceptProposedAction()
        if 切了项目:
            self.状态("已临时切换项目到 %s（重启后恢复原项目）" % os.path.basename(self.项目目录))
        # **只有最小化/隐藏时才 showNormal()**。
        # 以前无条件调用：窗口本来最大化（或全屏），拖一个文件进来
        # 就被还原成普通大小，面板宽度、滚动位置全变 ——
        # 用户只是拖了个文件，不是想把窗口缩小（同 closeEvent 的 P3-3）。
        if self.isMinimized() or not self.isVisible():
            状态 = getattr(self, "_拖放前窗态", None)
            if 状态 == "fullscreen":
                self.showFullScreen()
            elif 状态 == "maximized":
                self.showMaximized()
            else:
                self.showNormal()
        self.raise_()
        self.activateWindow()

    def _装载项目树不存配置(self, 目录):
        """装载项目树，但**不**把项目目录变成持久设置（拖放专用，P1-14）。

        旧实现是「装载之后把 配置["项目目录"] 还原回装载前的值」。
        那治不了根：装载项目树 已经把 `self.项目目录` 改成了新目录，
        而 存配置() 写盘用的是 `self.项目目录` —— 下一次存配置
        （退出、改字号、应用设置）照样把临时目录写死了。
        现在拆成两个字段：会话值 `self.项目目录`（只影响本次显示）、
        持久值 `self._持久项目目录`（只有它进配置文件）。
        """
        self.装载项目树(目录, 记住=False)


def 启动(参数=None):
    应用 = QApplication.instance() or QApplication(sys.argv)
    应用.setApplicationName("核工坊")
    窗 = 主窗()
    # 双击 .xht 文件时，系统会把路径作为参数传进来，直接打开它。
    # **所有**文件参数都要开：以前开完第一个就 break，
    # 选中三个文件「打开方式 → 核工坊」只出来一个，另两个悄悄没了。
    # 目录参数当作项目目录（和拖放同一个口径）。
    参数 = 参数 if 参数 is not None else sys.argv[1:]
    开过 = False
    for 项 in 参数:
        try:
            if os.path.isdir(项):
                窗.装载项目树(os.path.abspath(项))
            elif os.path.isfile(项):
                窗.打开(项)
                开过 = True
        except OSError:
            continue
    if 开过:
        窗.刷新标签()
    窗.show()
    return 应用.exec()


if __name__ == "__main__":
    sys.exit(启动())
