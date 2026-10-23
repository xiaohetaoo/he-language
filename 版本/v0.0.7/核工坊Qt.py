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

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QIcon, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMenu,
    QMessageBox, QPlainTextEdit, QSplitter, QTabBar, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget,
)

import 主题
import 配置
from 编辑器 import 编辑器

这里 = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, 这里)

import 核  # noqa: E402


def 图标路径(名):
    return os.path.join(这里, "素材", 名)


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
        版本 = QLabel("⎇  版本控制")
        版本.setObjectName("topBtn")
        版本.setCursor(Qt.PointingHandCursor)
        版本.mousePressEvent = lambda e: 主窗.状态("版本控制尚未接入 git")
        布局.addWidget(版本)

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

        self.刷新图标()

    def 刷新图标(self, 主题表=None):
        """按当前主题重画竖条图标。"""
        表 = 主题表 or getattr(self.主窗, "主题", {}) or {}
        取 = lambda 键, 备: 表.get(键, 备)
        形状表 = {键: 形状 for 键, 形状, _, _, _ in self._图标表}
        self.钮们["项目"].setPixmap(画图标(形状表["项目"], 取("图标项目", "#3574F0")))
        self.钮们["结构"].setPixmap(画图标(形状表["结构"], 取("图标结构", "#B58EF8")))
        self.钮们["运行"].setPixmap(画图标(形状表["运行"], 取("图标运行", "#4CAF6E")))
        self.钮们["设置"].setPixmap(画图标("齿轮", 取("图标设置", "#9DA0A8")))
        self.状态点.setPixmap(画图标("圆点", 取("图标状态点", "#6AAB73")))


class 主窗(QMainWindow):
    def __init__(self):
        super().__init__()
        self.内核 = 核
        self.配置 = 配置.读配置()
        self.主题名 = self.配置.get("主题", "深色")
        self.主题 = 主题.取主题(self.主题名)
        self.字号 = int(self.配置.get("字号", 12))
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
        主题.换主题(self, self.主题, self.字号)
        self._应用窗口外观()
        self._刷新图标()

        self.装载项目树(self.项目目录)
        self.新建()
        self._刷新标题()

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
        self.控制台.appendPlainText("在项目中查找：%s\n" % 词)
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
                        self.控制台.appendPlainText(
                            "%s:%d:  %s" % (相对, 号, 行.rstrip())
                        )
        self.控制台.appendPlainText("\n共 %d 处" % 命中)
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
        保留文档 = self.文档集[保留] if 0 <= 保留 < len(self.文档集) else None
        for 编 in list(self.文档集):
            if 编 is not 保留文档:
                编.已改 = False
                self.关闭文档(编, 强制=True)

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
            with open(编.文件路径, "w", encoding="utf-8", newline="\n") as f:
                f.write(编.取文本())
        except OSError as e:
            self.状态("保存失败：%s" % e)
            if 弹窗:
                QMessageBox.warning(self, "保存失败", str(e))
            return False
        编.已改 = False
        self.刷新标签(编)
        self._刷新标题()
        self.状态("已保存 %s" % os.path.basename(编.文件路径))
        return True

    def 保存当前(self):
        return self.保存(self.当前, 弹窗=True)

    def 另存为(self, 编=None):
        编 = 编 or self.当前
        if 编 is None:
            return False
        路径, _ = QFileDialog.getSaveFileName(
            self, "另存为", self._文件名(编),
            "核语言源文件 (*.xht);;所有文件 (*.*)",
        )
        if not 路径:
            return False
        编.文件路径 = os.path.abspath(路径)
        ok = self.保存(编)
        if ok:
            self.刷新标签(编)
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

    def _填目录(self, 节点, 目录):
        from PySide6.QtWidgets import QFileIconProvider

        提供 = QFileIconProvider()
        try:
            项 = sorted(os.scandir(目录), key=lambda e: (not e.is_dir(), e.name.lower()))
        except OSError:
            return
        for 条 in 项:
            if 条.name.startswith(".") or 条.name in ("__pycache__", "build", "dist"):
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
        self.显示行号 = not self.显示行号
        for d in self.文档集:
            d._行号隐藏 = not self.显示行号
            d.行号.setVisible(self.显示行号)
            d._更新行号宽()
        self.状态("行号已%s" % ("显示" if self.显示行号 else "隐藏"))
        self.存配置()

    def 切换缩进线(self):
        self.显示缩进线 = not self.显示缩进线
        for d in self.文档集:
            d.update()
        self.状态("缩进参考线已%s" % ("显示" if self.显示缩进线 else "隐藏"))
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
        if not self.当前.文件路径:
            self.状态("请先保存再运行（Ctrl+S）")
            return
        if self.当前.已改:
            self.保存(self.当前, 弹窗=False)
        self.停止(静默=True)
        self.清空控制台()
        命令 = self._内核命令(self.当前.文件路径)
        self.控制台.appendPlainText("> " + " ".join(命令[1:]))

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
            )
        except OSError as e:
            self.控制台.appendPlainText("启动失败：%s" % e)
            self.进程 = None
            return
        self.运行状态.setText("运行中…")
        self.运行状态.setStyleSheet("color: %s;" % self.主题["强调"])
        self.竖条.状态点.setStyleSheet("color: %s;" % self.主题["强调"])
        self._读线程 = threading.Thread(
            target=self._读输出, args=(self.进程,), daemon=True
        )
        self._读线程.start()
        self._轮询 = QTimer(self)
        self._轮询.timeout.connect(self._检查进程)
        self._轮询.start(80)

    def _读输出(self, 进程):
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
                    self._输出.put(块.decode("utf-8", "replace"))
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
            self.控制台.appendPlainText("\n[程序结束，返回 %d]\n" % 码)
            self.运行状态.setText("就绪")
            self.运行状态.setStyleSheet("")
            self.竖条.状态点.setStyleSheet("")
            self.状态("运行结束（返回 %s）" % 码)
            if self._轮询:
                self._轮询.stop()
                self._轮询 = None

    def _吸输出(self):
        while True:
            try:
                文本 = self._输出.get_nowait()
            except queue.Empty:
                return
            # 用 appendPlainText 保证每块输出从新行开始：
            # insertPlainText 会接在命令行尾巴上（曾出现「...xht你好世界」）
            self.控制台.appendPlainText(文本.rstrip("\n"))

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
        try:
            self.进程.kill()
        except OSError:
            pass
        self._收尾()
        if self._轮询:
            self._轮询.stop()
            self._轮询 = None
        if not 静默:
            self.控制台.appendPlainText("\n[已停止]\n")
            self.运行状态.setText("就绪")
            self.运行状态.setStyleSheet("")
            self.竖条.状态点.setStyleSheet("")
            self.状态("已停止")

    def 发送输入(self):
        文 = self.输入框.text()
        self.输入框.clear()
        if self.进程 is None or self.进程.poll() is not None:
            self.控制台.appendPlainText("（程序已结束，这句没发出去）\n")
            return
        try:
            self.进程.stdin.write((文 + "\n").encode("utf-8"))
            self.进程.stdin.flush()
            self.控制台.appendPlainText(文 + "\n")
        except (OSError, ValueError) as e:
            self.控制台.appendPlainText("发送失败：%s\n" % e)

    def 清空控制台(self):
        self.控制台.clear()

    def 检查语法(self):
        if not (self.当前 and self.当前.文件路径):
            self.状态("先保存文件再检查语法")
            return
        报告 = self.内核.未定义报告(None)
        try:
            代码, _ = self.内核.编译源码(self.当前.取文本(), self.当前.文件路径, 报告)
        finally:
            报告.保存()
        self.状态("检查通过" if 代码 is not None else "语法有误，见运行窗口")

    def 打开未定义清单(self):
        路径 = os.path.join(self.项目目录, self.内核.未定义文件名)
        if os.path.exists(路径):
            self.打开(路径)
        else:
            self.状态("还没有未定义记录")

    # ================= 视图与主题 =================

    def 切换注释(self):
        if self.当前:
            self.当前.切换注释()

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
        self.字号 = max(9, min(22, self.字号 + 差))
        for d in self.文档集:
            d.设置字体(self.字号)
        self.状态("字号 %d" % self.字号)
        self.存配置()

    def 换主题(self, 名):
        self.主题 = 主题.取主题(名, self.主题)
        self.主题名 = self.主题["名"]
        主题.换主题(self, self.主题, self.字号)
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

    def 弹主菜单(self, 锚):
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
            动作 = QAction(名, self)
            动作.triggered.connect(lambda _=False, c=命令: c())
            文件.addAction(动作)

        最近 = 文件.addMenu("最近打开")
        for 路径 in self.最近[:10]:
            if not os.path.isfile(路径):
                continue
            动作 = QAction(os.path.basename(路径), self)
            动作.setToolTip(路径)
            动作.triggered.connect(lambda _=False, p=路径: self.打开(p))
            最近.addAction(动作)
        if not 最近.actions():
            空 = QAction("（空）", self)
            空.setEnabled(False)
            最近.addAction(空)
        菜单.addSeparator()

        编 = 菜单.addMenu("编辑")
        for 名, 命令 in (
            ("撤销", lambda: self.当前 and self.当前.undo()),
            ("重做", lambda: self.当前 and self.当前.redo()),
        ):
            动作 = QAction(名, self)
            动作.triggered.connect(lambda _=False, c=命令: c())
            编.addAction(动作)
        编.addSeparator()
        for 名, 命令 in (
            ("剪切", lambda: self.当前 and self.当前.cut()),
            ("复制", lambda: self.当前 and self.当前.copy()),
            ("粘贴", lambda: self.当前 and self.当前.paste()),
            ("全选", lambda: self.当前 and self.当前.selectAll()),
        ):
            动作 = QAction(名, self)
            动作.triggered.connect(lambda _=False, c=命令: c())
            编.addAction(动作)
        编.addSeparator()
        for 名, 命令 in (
            ("注释 / 取消注释", self.切换注释),
            ("查找 / 替换…", self.查找),
            ("转到行…", self.跳到行),
        ):
            动作 = QAction(名, self)
            动作.triggered.connect(lambda _=False, c=命令: c())
            编.addAction(动作)
        菜单.addSeparator()

        运 = 菜单.addMenu("运行")
        for 名, 命令 in (
            ("运行", self.运行),
            ("停止", lambda: self.停止()),
            ("检查语法", self.检查语法),
            ("未定义清单", self.打开未定义清单),
        ):
            动作 = QAction(名, self)
            动作.triggered.connect(lambda _=False, c=命令: c())
            运.addAction(动作)
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
        ):
            动作 = QAction(名, self)
            动作.triggered.connect(lambda _=False, c=命令: c())
            视.addAction(动作)
        菜单.addSeparator()

        设置 = QAction("设置…", self)
        设置.triggered.connect(self.打开设置)
        菜单.addAction(设置)
        菜单.exec(锚.mapToGlobal(锚.rect().bottomLeft()))

    def 弹出项目菜单(self, 锚):
        菜单 = QMenu(self)
        动作 = QAction("切换项目文件夹…", self)
        动作.triggered.connect(self.选择项目目录)
        菜单.addAction(动作)
        动作2 = QAction("刷新项目树", self)
        动作2.triggered.connect(lambda: self.装载项目树(self.项目目录))
        菜单.addAction(动作2)
        菜单.exec(锚.mapToGlobal(锚.rect().bottomLeft()))

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

    def _应用窗口外观(self):
        try:
            import ctypes

            dwm = ctypes.WinDLL("dwmapi", use_last_error=True)
            句柄 = int(self.winId())
            深 = ctypes.c_int(1 if self.主题名 == "深色" else 0)
            dwm.DwmSetWindowAttribute(句柄, 20, ctypes.byref(深), ctypes.sizeof(深))
            圆 = ctypes.c_int(2)
            dwm.DwmSetWindowAttribute(句柄, 33, ctypes.byref(圆), ctypes.sizeof(圆))
        except Exception:
            pass

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
        for 编 in list(self.文档集):
            if 编.已改:
                答 = QMessageBox.question(
                    self, "退出确认", "「%s」还没保存，要保存吗？" % self._文件名(编),
                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                )
                if 答 == QMessageBox.Cancel:
                    return
                if 答 == QMessageBox.Yes and not self.保存(编):
                    return
        self.停止(静默=True)
        self.存配置()
        QApplication.instance().quit()

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
