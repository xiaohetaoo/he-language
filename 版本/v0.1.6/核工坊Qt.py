# -*- coding: utf-8 -*-
"""核工坊 Qt 版主窗口 —— 严格模仿 PyCharm 新 UI。

布局（自上而下、自左而右）：
    顶部单行：图标 | ☰ 菜单 | 项目名 | 版本控制 | …… | ▶ 运行 | ⚙ | 搜索 | 窗口按钮
    主体：左侧竖条(项目/结构/运行/设置) | 项目树 | 编辑器 | 右侧对照表
    底部：运行窗口（含输入行）
    状态栏：项目 | 提示 | 行/列 | 编码 | 缩进

内核（转译/执行）全部复用 核.py，一行不改。
"""

import os
import queue
import subprocess
import sys
import threading
import time

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import (
    QAction, QIcon, QKeySequence, QPixmap, QShortcut, QTextCursor,
)
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMenu, QMessageBox, QPlainTextEdit, QSplitter, QTabBar,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
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
    def __init__(self, 字, 提示, 关闭类=False, 父=None):
        super().__init__(字, 父)
        self.setObjectName("关闭钮" if 关闭类 else "窗口钮")
        self.setToolTip(提示)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedSize(46, 32)
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
        self.setFixedHeight(44)

        布局 = QHBoxLayout(self)
        布局.setContentsMargins(10, 0, 0, 0)
        布局.setSpacing(4)

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
        self.运行钮.setFixedWidth(30)
        self.运行钮.mousePressEvent = lambda e: 主窗.运行()
        布局.addWidget(self.运行钮)

        # 设置入口只在左侧竖条底部保留一个（顶行不再重复放齿轮）

        self.搜索 = QLineEdit()
        self.搜索.setObjectName("searchBox")
        self.搜索.setPlaceholderText("搜索")
        self.搜索.setFixedWidth(170)
        self.搜索.returnPressed.connect(主窗.查找)
        布局.addWidget(self.搜索)
        布局.addSpacing(6)

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
            self.最大化.setText("□")
        else:
            self.主窗.showMaximized()
            self.最大化.setText("❐")

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
        布局.setContentsMargins(6, 8, 6, 8)
        布局.setSpacing(6)

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
        self.制表宽 = int(self.配置.get("制表宽", 4))
        self.显示缩进线 = bool(self.配置.get("缩进线", True))
        self.显示行号 = bool(self.配置.get("行号", True))
        self.自动高亮 = bool(self.配置.get("自动高亮", True))
        self.最近 = list(self.配置.get("最近", []))
        self.文档集 = []
        self.当前 = None
        self.项目目录 = self.配置.get("项目目录") or _默认项目目录()
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

        self._建界面()
        self._绑快捷键()
        self._套样式()
        self._应用窗口外观()
        self._刷新图标()

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

    def _标记退出中(self):
        self._收到退出信号 = True

    def _还原窗口尺寸(self):
        """按上次保存的尺寸和位置还原；越界或异常就回默认值。"""
        尺寸 = self.配置.get("窗口尺寸", "")
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
        self.resize(宽, 高)

        位置 = self.配置.get("窗口位置", "")
        if "," in 位置:
            try:
                x, y = (int(v) for v in 位置.split(","))
                if 屏 is not None and 屏.contains(x + 50, y + 30):
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
        头行.setFixedHeight(32)
        头布局 = QHBoxLayout(头行)
        头布局.setContentsMargins(10, 0, 8, 0)
        头布局.setSpacing(6)
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
        self.屑.setFixedHeight(26)
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
        图标 = QPixmap(图标路径("核图标_128.png"))
        if not 图标.isNull():
            图.setPixmap(
                图标.scaled(84, 84, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            图.setAlignment(Qt.AlignCenter)
            欢迎.addWidget(图)

        标题 = QLabel("核语言")
        标题.setAlignment(Qt.AlignCenter)
        标题.setStyleSheet("font-size: 30px; font-weight: bold; background: transparent;")
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

        头 = QLabel("  语法对照表")
        头.setObjectName("panelHeader")
        头.setFixedHeight(32)
        布局.addWidget(头)

        self.对照 = QPlainTextEdit()
        self.对照.setObjectName("refTable")
        self.对照.setReadOnly(True)
        布局.addWidget(self.对照, 1)

        框.setMinimumWidth(200)
        self._填对照表()
        return 框

    def _填对照表(self):
        c = self.内核
        行 = []
        for 标题, 表, 宽 in (
            ("关键字", c.关键词表, 10),
            ("内置函数", c.函数表, 12),
            ("方法", c.方法表, 10),
            ("关键字参数", c.参数表, 8),
            ("异常类型", c.异常表, 10),
        ):
            行.append("%s (%d)" % (标题, len(表)))
            行.append("")
            for 中, 英 in sorted(表.items()):
                行.append("  %-*s = %s" % (宽, 中, 英))
            行.append("")
        self.对照.setPlainText("\n".join(行))

    def _建运行窗(self):
        框 = QWidget()
        布局 = QVBoxLayout(框)
        布局.setContentsMargins(0, 0, 0, 0)
        布局.setSpacing(0)

        头 = QWidget()
        头.setObjectName("runHeader")
        头.setFixedHeight(30)
        头布局 = QHBoxLayout(头)
        头布局.setContentsMargins(14, 0, 10, 0)
        头布局.setSpacing(14)

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
        输入行.setFixedHeight(40)
        输入布局 = QHBoxLayout(输入行)
        输入布局.setContentsMargins(14, 5, 10, 5)
        输入布局.setSpacing(8)
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
        条.setFixedHeight(26)
        布局 = QHBoxLayout(条)
        布局.setContentsMargins(14, 0, 14, 0)
        布局.setSpacing(18)
        self.状态项目 = QLabel("")
        self.状态项目.setObjectName("statusLeft")
        self.状态左 = QLabel("")
        self.状态左.setObjectName("statusLeft")
        布局.addWidget(self.状态项目)
        布局.addWidget(self.状态左)
        布局.addStretch(1)
        self.状态右 = QLabel("核语言   空格 4   UTF-8")
        self.状态右.setObjectName("statusRight")
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

    def 重命名当前(self):
        """F2 重命名当前文件（另存为新名字后替换旧标签）。"""
        if self.当前 is None or not self.当前.文件路径:
            self.状态("先保存文件再重命名")
            return
        from PySide6.QtWidgets import QInputDialog

        旧名 = os.path.basename(self.当前.文件路径)
        新名, 确定 = QInputDialog.getText(self, "重命名", "新文件名：", text=旧名)
        if not 确定 or not 新名 or 新名 == 旧名:
            return
        旧路径 = self.当前.文件路径
        新路径 = os.path.join(os.path.dirname(旧路径), 新名)
        try:
            os.rename(旧路径, 新路径)
        except OSError as e:
            self.状态("重命名失败：%s" % e)
            return
        self.当前.文件路径 = 新路径
        self.刷新标签(self.当前)
        self._刷新标题()
        self.状态("已重命名为 %s" % 新名)

    def 在项目中查找(self):
        """Ctrl+Shift+F：在项目所有 .xht 里搜索文字，结果列在控制台。"""
        from PySide6.QtWidgets import QInputDialog

        词, 确定 = QInputDialog.getText(self, "在项目中查找", "要查找的文字：")
        if not 确定 or not 词:
            return
        命中 = 0
        self.清空控制台()
        self._写控制台("在项目中查找：%s\n" % 词)
        for 目录, 子目录, 文件 in os.walk(self.项目目录):
            子目录[:] = [
                d for d in 子目录
                if not d.startswith(".") and d not in ("__pycache__", "build", "dist", "版本")
            ]
            for 名 in 文件:
                if not 名.endswith(".xht"):
                    continue
                全 = os.path.join(目录, 名)
                try:
                    with open(全, encoding="utf-8", errors="replace") as f:
                        行们 = f.readlines()
                except OSError:
                    continue
                for 号, 行 in enumerate(行们, 1):
                    if 词 in 行:
                        命中 += 1
                        相对 = os.path.relpath(全, self.项目目录)
                        self._写控制台(
                            "%s:%d:  %s\n" % (相对, 号, 行.rstrip())
                        )
        self._写控制台("\n共 %d 处\n" % 命中)
        self.状态("项目内找到 %d 处" % 命中)

    # ================= 文档管理 =================

    def 新建(self):
        编 = 编辑器(self)
        编.已改 = False
        编.hide()
        self.文档集.append(编)
        self.标签栏.addTab("未命名")
        self.标签栏.setCurrentIndex(len(self.文档集) - 1)
        self._显示文档(编)
        return 编

    def _显示文档(self, 编):
        self.无文档提示.hide()
        if self.当前 is not None and self.当前 is not 编:
            self.当前.hide()
        if 编.parent() is None:
            self.容器.layout().addWidget(编)
        编.show()
        self.当前 = 编
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
            动作 = QAction(名, self)
            动作.triggered.connect(lambda _=False, c=命令: c())
            菜单.addAction(动作)
        菜单.exec(self.标签栏.mapToGlobal(位置))

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
        return os.path.basename(编.文件路径) if 编.文件路径 else "未命名"

    def 关闭文档(self, 编, 强制=False):
        if 编.已改 and not 强制:
            答 = QMessageBox.question(
                self, "保存确认", "「%s」已修改，要保存吗？" % self._文件名(编),
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            )
            if 答 == QMessageBox.Cancel:
                return False
            if 答 == QMessageBox.Yes and not self.保存(编):
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

    def 打开(self, 路径):
        for d in self.文档集:
            if d.文件路径 and os.path.normcase(d.文件路径) == os.path.normcase(路径):
                self._显示文档(d)
                return d
        if not os.path.isfile(路径):
            self.状态("文件不存在：%s" % 路径)
            return None
        try:
            内容 = self.内核.读源码(路径)
        except OSError as e:
            self.状态("打不开文件：%s" % e)
            return None
        if "\x00" in 内容:
            self.状态("这不是文本文件：%s" % os.path.basename(路径))
            return None
        编 = 编辑器(self)
        编.文件路径 = os.path.abspath(路径)
        编.置文本(内容.replace("\r\n", "\n").replace("\r", "\n"))
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
            with open(临时, "w", encoding="utf-8", newline="\n") as f:
                f.write(文本)
                f.flush()
                os.fsync(f.fileno())
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
        # 目标已经存在时，再确认一次。
        # 系统的「另存为」对话框一般会自己问「要不要覆盖」，但那依赖原生对话框
        # 的行为（Qt 用非原生实现时不问）。这里自己兜住底 ——
        # 覆盖是破坏性的，不该只靠对话框的实现细节。
        if os.path.exists(路径) and 路径 != os.path.abspath(编.文件路径 or ""):
            答 = QMessageBox.question(
                self, "确认覆盖", "「%s」已经存在，要覆盖吗？" % os.path.basename(路径),
                QMessageBox.Yes | QMessageBox.No,
            )
            if 答 != QMessageBox.Yes:
                return False
        编.文件路径 = 路径
        ok = self.保存(编)
        if ok:
            self.刷新标签(编)
            self.加最近(路径)
        return ok

    # ================= 项目树 =================

    def 装载项目树(self, 目录):
        self.项目目录 = 目录
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
            项 = sorted(os.scandir(目录), key=lambda e: (not e.is_dir(), e.name.lower()))
        except OSError:
            return
        for 条 in 项:
            if 条.name.startswith(".") or 条.name in _隐藏项:
                continue
            if 条.is_dir():
                子 = QTreeWidgetItem(节点, [条.name])
                子.setIcon(0, 提供.icon(QFileIconProvider.Folder))
                子.setData(0, Qt.UserRole, 条.path)
                QTreeWidgetItem(子, ["…"])
            elif 条.name.endswith((".xht", ".py", ".txt", ".md", ".json")):
                子 = QTreeWidgetItem(节点, [条.name])
                子.setIcon(0, 提供.icon(QFileIconProvider.File))
                子.setData(0, Qt.UserRole, 条.path)

    def _双击树(self, 项, _列):
        路径 = 项.data(0, Qt.UserRole)
        if not 路径:
            return
        if os.path.isdir(路径):
            if 项.childCount() == 1 and 项.child(0).text(0) == "…":
                项.takeChild(0)
                self._填目录(项, 路径)
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
                动作 = QAction(名, self)
                动作.triggered.connect(lambda _=False, c=命令: c())
                菜单.addAction(动作)
        else:
            for 名, 命令 in (
                ("打开", lambda: self.打开(路径)),
                ("复制路径", lambda: QApplication.instance().clipboard().setText(路径)),
                ("在文件管理器中显示", lambda: self._在管理器显示路径(路径)),
            ):
                动作 = QAction(名, self)
                动作.triggered.connect(lambda _=False, c=命令: c())
                菜单.addAction(动作)
        菜单.addSeparator()
        刷新 = QAction("刷新项目树", self)
        刷新.triggered.connect(lambda: self.装载项目树(self.项目目录))
        菜单.addAction(刷新)
        菜单.exec(self.树.mapToGlobal(位置))

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
        self.制表宽 = max(1, int(宽))
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
            if not self.保存(self.当前, 弹窗=False):
                if not self.另存为(self.当前):
                    self.状态("保存失败，已取消运行")
                    return
        self.停止(静默=True)
        self.清空控制台()
        # 队列要在开新进程之前换一个新的：旧读线程可能已经在关流前读到了
        # 数据、只是还没被 _吸输出 取走，那些残留会打在新一轮运行的开头。
        换队列 = getattr(self, "_输出", None)
        self._输出 = queue.Queue()
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
        self.运行状态.setStyleSheet("color: %s;" % self.主题["强调"])
        self.竖条.设状态点("运行")
        self._读线程 = threading.Thread(
            target=self._读输出, args=(self.进程, self._输出), daemon=True
        )
        self._读线程.start()
        self._轮询 = QTimer(self)
        self._轮询.timeout.connect(self._检查进程)
        self._轮询.start(80)

    def _读输出(self, 进程, 队列):
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
        try:
            while True:
                try:
                    块 = 进程.stdout.read1(65536)
                except (BlockingIOError, InterruptedError):
                    块 = b""
                except (OSError, ValueError):
                    break
                if 块:
                    队列.put(块.decode("utf-8", "replace"))
                    空读 = 0
                    continue
                空读 += 1
                已结束 = 进程.poll() is not None
                if 已结束 and 空读 >= 3:
                    break
                if not 已结束:
                    time.sleep(0.03)
        finally:
            pass

    def _检查进程(self):
        self._吸输出()
        if self.进程 is not None and self.进程.poll() is not None:
            码 = self.进程.returncode
            读 = getattr(self, "_读线程", None)
            if 读 is not None and 读.is_alive():
                读.join(timeout=1.0)
            self._吸输出()
            self._收尾()
            self._写控制台("\n[程序结束，返回 %d]\n" % 码)
            self.运行状态.setText("就绪")
            self.运行状态.setStyleSheet("")
            self.竖条.设状态点("空闲")
            self.状态("运行结束（返回 %s）" % 码)
            if self._轮询:
                self._轮询.stop()
                self._轮询 = None

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

    def _收尾(self):
        进程 = self.进程
        if 进程 is None:
            return
        for 名 in ("stdin", "stdout"):
            流 = getattr(进程, 名, None)
            if 流:
                try:
                    流.close()
                except (OSError, ValueError):
                    pass
        self.进程 = None

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
            self.运行状态.setStyleSheet("")
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
        游 = self.控制台.textCursor()
        游.movePosition(QTextCursor.End)
        self.控制台.setTextCursor(游)
        self.控制台.insertPlainText(文本)
        条 = self.控制台.verticalScrollBar()
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

            # 传项目目录：打包版的 版本/ 不在 exe 里，得去项目目录找
            self._版本历史 = 帮助窗口.版本历史对话框(
                self, 核.版本, self.项目目录
            )
            self._版本历史.show()
            self._版本历史.raise_()
        except Exception as e:  # noqa: BLE001
            self.状态("打不开版本历史：%s" % e)

    def 关于(self):
        try:
            import 帮助窗口

            self._关于 = 帮助窗口.关于对话框(self, 核.版本)
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

            self._版本窗 = 版本控制窗口.版本控制窗口(self, self.项目目录)
            self._版本窗.show()
            self._版本窗.raise_()
        except Exception as e:  # noqa: BLE001
            self.状态("打不开版本控制面板：%s" % e)

    def 快速打开(self):
        try:
            import 快速打开

            self._快速 = 快速打开.快速打开(self)
            self._快速.exec()
        except Exception as e:  # noqa: BLE001
            self.状态("快速打开失败：%s" % e)

    def 查找(self):
        """Ctrl+F：优先用顶行搜索框的内容，否则打开查找对话框。"""
        文 = self.顶行.搜索.text().strip()
        if self.当前 is not None and 文:
            if not self.当前.查找下一个(文):
                self.状态("没找到：%s" % 文)
            return
        try:
            import 查找对话框

            self._查找窗 = 查找对话框.查找对话框(self, self.当前)
            self._查找窗.show()
            self._查找窗.raise_()
        except Exception as e:  # noqa: BLE001
            self.状态("打不开查找框：%s" % e)

    def 跳到行(self):
        try:
            import 查找对话框

            查找对话框.跳转对话框(self, self.当前).exec()
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

            设置窗口Qt.设置对话框(self).exec()
        except Exception as e:  # noqa: BLE001
            self.状态("设置窗口打不开：%s" % e)

    def 状态(self, 文本):
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
            尾 = "   （已选 %d 字符）" % len(游.selectedText())
        self.状态右.setText(
            "核语言   空格 %d   UTF-8   行 %d, 列 %d%s" % (self.制表宽, 行, 列, 尾)
        )

    # ================= 菜单 =================

    @staticmethod
    def _加动作(菜单, 文本, 命令, 提示=None):
        """往菜单里加一个动作。

        父对象必须是**菜单**而不是主窗：菜单用完就销毁，
        挂在主窗上的动作不会被回收 —— 每开一次菜单就往主窗里堆
        四十来个 QAction，反复点几次内存就 steadily 涨上去。
        """
        动作 = QAction(文本, 菜单)
        if 提示:
            动作.setToolTip(提示)
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
        for 名, 命令 in (
            ("新建", self.新建),
            ("打开…", self.打开文件),
            ("快速打开…", self.快速打开),
            ("打开文件夹…", self.选择项目目录),
            ("保存", self.保存当前),
            ("另存为…", self.另存为),
            ("关闭标签", self.关闭当前),
            ("退出", self.退出),
        ):
            文件.addAction(self._加动作(文件, 名, 命令))

        最近 = 文件.addMenu("最近打开")
        for 路径 in self.最近[:10]:
            if not os.path.isfile(路径):
                continue
            最近.addAction(
                self._加动作(最近, os.path.basename(路径), lambda p=路径: self.打开(p), 路径)
            )
        if not 最近.actions():
            空 = QAction("（空）", 最近)
            空.setEnabled(False)
            最近.addAction(空)
        菜单.addSeparator()

        编 = 菜单.addMenu("编辑")
        for 名, 命令 in (
            ("撤销", lambda: self.当前 and self.当前.undo()),
            ("重做", lambda: self.当前 and self.当前.redo()),
        ):
            编.addAction(self._加动作(编, 名, 命令))
        编.addSeparator()
        for 名, 命令 in (
            ("剪切", lambda: self.当前 and self.当前.cut()),
            ("复制", lambda: self.当前 and self.当前.copy()),
            ("粘贴", lambda: self.当前 and self.当前.paste()),
            ("全选", lambda: self.当前 and self.当前.selectAll()),
        ):
            编.addAction(self._加动作(编, 名, 命令))
        编.addSeparator()
        for 名, 命令 in (
            ("注释 / 取消注释", self.切换注释),
            ("查找 / 替换…", self.查找),
            ("转到行…", self.跳到行),
        ):
            编.addAction(self._加动作(编, 名, 命令))
        菜单.addSeparator()

        码 = 菜单.addMenu("代码")
        for 名, 命令 in (
            ("折叠当前块", self.折叠当前),
            ("展开当前块", self.展开当前),
            ("全部折叠", self.全部折叠),
            ("全部展开", self.全部展开),
        ):
            码.addAction(self._加动作(码, 名, 命令))
        菜单.addSeparator()

        运 = 菜单.addMenu("运行")
        for 名, 命令 in (
            ("运行", self.运行),
            ("停止", lambda: self.停止()),
            ("检查语法", self.检查语法),
            ("未定义清单", self.打开未定义清单),
        ):
            运.addAction(self._加动作(运, 名, 命令))
        菜单.addSeparator()

        视 = 菜单.addMenu("视图")
        for 名, 命令 in (
            ("深色主题", lambda: self.换主题("深色")),
            ("浅色主题", lambda: self.换主题("浅色")),
            ("项目栏", self.切换项目栏),
            ("语法对照表", self.切换对照表),
            ("运行窗口", self.切换运行窗),
            ("显示行号", self.切换行号),
            ("显示缩进参考线", self.切换缩进线),
            ("增大字号", lambda: self.改字号(1)),
            ("减小字号", lambda: self.改字号(-1)),
            ("版本控制", self.版本控制面板),
        ):
            视.addAction(self._加动作(视, 名, 命令))
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

        菜单.addAction(self._加动作(菜单, "设置…", self.打开设置))
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

    def 存配置(self):
        """把界面状态写盘，下次启动还原。"""
        self.配置.update({
            "主题": self.主题名,
            "字号": self.字号,
            "制表宽": self.制表宽,
            "缩进线": self.显示缩进线,
            "行号": self.显示行号,
            "自动高亮": self.自动高亮,
            "最近": self.最近[:12],
            "项目目录": self.项目目录,
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

    def _收尾退出(self):
        """停子进程、停后台线程、写配置。"""
        self.停止(静默=True)
        查询器 = getattr(self, "_版本查询", None)
        if 查询器 is not None:
            # 等后台的 git 查询收尾再退出，免得工作线程在解释器拆栈时
            # 还回来调 _完成（那时窗口对象可能已经先没了）。
            查询器.停()
        self.存配置()

    def _逐个处理未保存(self):
        """有未保存的文档就逐个问要不要保存（模态版）。

        ⚠️ **只能在「用户主动操作」的上下文里调，绝不能在退出流程里调**。
        程序自己 quit() 时会同步走到 closeEvent，那时弹模态框会把
        事件循环卡死（实测）。退出路径统一用非模态的 _问要不要保存()。

        现在仍有调用的是「关闭全部」这类菜单动作 —— 那些不涉及退出流程。
        返回 True = 可以继续；False = 用户选了「取消」，不该继续。
        """
        for 编 in list(self.文档集):
            if not 编.已改:
                continue
            答 = QMessageBox.question(
                self, "保存确认", "「%s」已修改，要保存吗？" % self._文件名(编),
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            )
            if 答 == QMessageBox.Cancel:
                return False
            if 答 == QMessageBox.Yes and not self.保存(编):
                return False
        return True

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
        # 没有未保存的改动 → 直接关，不用打扰用户
        if not any(编.已改 for 编 in self.文档集):
            self._收尾退出()
            事件.accept()
            return

        # 有未保存的改动 → 先让窗口关掉（accept），再弹非模态框问。
        # 不能 ignore()：那会把程序自己的 quit() 也卡住。
        事件.accept()
        self._收尾退出()
        if getattr(self, "_关窗确认中", False):
            return          # 已经在问了，别再弹第二个
        self._关窗确认中 = True
        self._问要不要保存()

    def _问要不要保存(self):
        """非模态地问「要不要保存」，答完再决定关不关。

        为什么不用 QMessageBox.question：那是模态的，会开自己的事件循环。
        在 closeEvent 里调它会和外层的退出流程抢事件循环 —— 程序卡死。
        这里用 QMessageBox 实例 + open()（非模态），完事再关掉。

        用户选「取消」时把窗口重新显示出来 —— 刚才为了不卡住退出流程
        已经 accept() 让它关上了。
        """
        待处理 = [编 for 编 in self.文档集 if 编.已改]
        if not 待处理:
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
        框.button(QMessageBox.Save).setText("保存")
        框.button(QMessageBox.Discard).setText("不保存")
        框.button(QMessageBox.Cancel).setText("取消")

        def 拉回来():
            """用户反悔了 —— 把窗口重新显示出来。"""
            self.showNormal()
            self.raise_()
            self.activateWindow()

        def 选好了(答):
            框.deleteLater()
            if 答 == QMessageBox.Cancel:
                self._关窗确认中 = False
                拉回来()
                return
            if 答 == QMessageBox.Save and not self.保存(编):
                self._关窗确认中 = False
                拉回来()
                return
            # 这一份处理完了，接着问下一份。
            # **必须延迟到下一轮事件循环**，不能在这里直接递归调 ——
            # 这里还在那个确认框自己的事件循环里，直接再 open() 一个框
            # 会形成嵌套的模态/非模态循环，退出流程就卡在里面出不来。
            # 实测（冒烟测试）就是这样挂死的：栈上是
            #   收 → closeEvent → _问要不要保存 → 选好了 → _问要不要保存
            self._关窗确认中 = False
            QTimer.singleShot(0, self._问要不要保存)

        框.finished.connect(选好了)
        框.open()
        self._关窗框 = 框

    def _真正关窗(self):
        """确认完了：收尾并关掉窗口。"""
        self._收尾退出()
        self._正在退出 = True
        self.close()

    # ================= 拖放 =================

    def dragEnterEvent(self, 事件):
        if 事件.mimeData().hasUrls():
            事件.acceptProposedAction()

    def dropEvent(self, 事件):
        for url in 事件.mimeData().urls():
            路径 = url.toLocalFile()
            if os.path.isdir(路径):
                self.装载项目树(路径)
            elif 路径.lower().endswith(".xht"):
                self.打开(路径)
        事件.acceptProposedAction()
        self.showNormal()
        self.raise_()
        self.activateWindow()


def 启动(参数=None):
    应用 = QApplication.instance() or QApplication(sys.argv)
    应用.setApplicationName("核工坊")
    窗 = 主窗()
    # 双击 .xht 文件时，系统会把路径作为参数传进来，直接打开它
    参数 = 参数 if 参数 is not None else sys.argv[1:]
    for 项 in 参数:
        if os.path.isfile(项):
            窗.打开(项)
            break
    窗.show()
    return 应用.exec()


if __name__ == "__main__":
    sys.exit(启动())
