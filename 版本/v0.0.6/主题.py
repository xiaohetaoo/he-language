# -*- coding: utf-8 -*-
"""核工坊的主题系统 —— 全部配色与控件样式的唯一来源。

设计：一个主题 = 一份色表 + 一份 QSS 模板。
换主题只需换「色表」，QSS 用字符串替换生成，不用逐个控件改色。
这是相比 tkinter 版最大的维护性提升（原来要改 101 处）。

新增主题只要往 `主题集` 里加一份色表即可。
"""

# ---------------------------------------------------------------------------
# 深色（PyCharm 2024 Darcula 真实取值）
# ---------------------------------------------------------------------------

深色 = {
    "名": "深色",
    # 三档层次：编辑器最暗、面板中间、浮层最亮
    "编辑器": "#1E1F22",
    "面板": "#2B2D30",
    "浮层": "#313438",
    "窗口": "#2B2D30",
    "边框": "#393B40",
    "分隔线": "#393B40",
    # 文字
    "文本": "#DFE1E5",
    "次要文本": "#B2B6BE",
    "禁用文本": "#6F737A",
    # 编辑器元素
    "行号底": "#1E1F22",
    "行号字": "#9AA0AB",
    "当前行": "#22252A",
    "选区": "#2E436E",
    "光标": "#DFE1E5",
    "缩进线": "#2A2C30",
    # 语法高亮
    "注释": "#9197A0",
    "字符串": "#6AAB73",
    "数字": "#2AACB8",
    "关键字": "#CF8E6D",
    "内置": "#D5B778",
    "函数名": "#56A8F5",
    # 交互
    "强调": "#3574F0",
    "悬停": "#393B40",
    "按下": "#43454A",
    "选中行": "#2E436E",
    "错误": "#F75464",
    "警告": "#D5B778",
    "成功": "#6AAB73",
    "关闭红": "#C42B1C",
    # 控制台
    "控制台底": "#1E1F22",
    "控制台字": "#BCBEC4",
}

# ---------------------------------------------------------------------------
# 浅色（PyCharm Light）
# ---------------------------------------------------------------------------

浅色 = {
    "名": "浅色",
    "编辑器": "#FFFFFF",
    "面板": "#F7F8FA",
    "浮层": "#EDEFF2",
    "窗口": "#F7F8FA",
    "边框": "#D6DAE0",
    "分隔线": "#D6DAE0",
    "文本": "#1F2329",
    "次要文本": "#5F6672",
    "禁用文本": "#9AA0A8",
    "行号底": "#F7F8FA",
    "行号字": "#6E747D",
    "当前行": "#F2F6FC",
    "选区": "#CFE2FF",
    "光标": "#1F2329",
    "缩进线": "#E8EBEF",
    "注释": "#6D737B",
    "字符串": "#067D17",
    "数字": "#1750EB",
    "关键字": "#8F4E00",
    "内置": "#8A6D00",
    "函数名": "#005FAB",
    "强调": "#3574F0",
    "悬停": "#E6E9ED",
    "按下": "#D8DCE2",
    "选中行": "#D5E5FF",
    "错误": "#C7221F",
    "警告": "#8A6D00",
    "成功": "#067D17",
    "关闭红": "#C42B1C",
    "控制台底": "#FFFFFF",
    "控制台字": "#3A3F45",
}

主题集 = {"深色": 深色, "浅色": 浅色}

#: 等宽字体候选（按优先级）
等宽候选 = ("Cascadia Mono", "JetBrains Mono", "Consolas", "Courier New")
#: 界面字体
界面字体 = "Microsoft YaHei UI"


# ---------------------------------------------------------------------------
# QSS 模板 —— 所有控件的样式都集中在这里
# ---------------------------------------------------------------------------

_QSS = """
/* 基础 */
QWidget {
    background: __窗口__;
    color: __文本__;
    font-family: "__界面字体__";
    font-size: 13px;
}
QMainWindow { background: __窗口__; }
QToolTip {
    background: __浮层__; color: __文本__;
    border: 1px solid __边框__; border-radius: 6px; padding: 5px 8px;
}

/* 外框（圆角无边框窗口） */
#rootFrame {
    background: __窗口__;
    border: 1px solid __边框__;
    border-radius: 12px;
}

/* 标题栏 */
#titleBar { background: __窗口__; border-top-left-radius: 12px; border-top-right-radius: 12px; }
#titleText { color: __文本__; font-size: 13px; }
#brandMark { background: transparent; }
#menuBtn {
    color: __次要文本__; font-size: 15px;
    padding: 4px 10px; border-radius: 6px; background: transparent;
}
#menuBtn:hover { background: __悬停__; color: __文本__; }

/* 窗口按钮 */
#winBtn {
    color: __次要文本__; font-size: 13px;
    background: transparent; padding: 0px;
}
#winBtn:hover { background: __悬停__; color: __文本__; }
#closeBtn { color: __次要文本__; background: transparent; }
#closeBtn:hover { background: __关闭红__; color: #FFFFFF; }

/* 搜索框 */
#searchBox {
    background: __编辑器__; color: __文本__;
    border: 1px solid __边框__; border-radius: 6px;
    padding: 5px 10px; font-size: 12px;
    selection-background-color: __选区__;
}
#searchBox:focus { border: 1px solid __强调__; }

/* 主工具条 */
#toolBar { background: __窗口__; border-bottom: 1px solid __边框__; }
#toolBtn {
    color: __文本__; background: transparent;
    padding: 6px 12px; border-radius: 6px; font-size: 13px;
}
#toolBtn:hover { background: __悬停__; }
#toolBtn:pressed { background: __按下__; }
#crumb { color: __次要文本__; font-size: 12px; background: transparent; }

/* 分栏 */
QSplitter::handle { background: __分隔线__; }
QSplitter::handle:horizontal { width: 1px; }
QSplitter::handle:vertical { height: 1px; }
QSplitter::handle:hover { background: __强调__; }

/* 面板头 */
#panelHeader {
    background: __窗口__; color: __次要文本__;
    font-size: 12px; border-bottom: 1px solid __边框__;
}

/* 项目树 */
QTreeWidget {
    background: __面板__; color: __文本__;
    border: none; outline: none; font-size: 13px;
}
QTreeWidget::item { height: 24px; padding-left: 2px; }
QTreeWidget::item:hover { background: __悬停__; }
QTreeWidget::item:selected { background: __选中行__; color: #FFFFFF; }
QTreeWidget::branch { background: transparent; }

/* 标签栏 */
#tabBar { background: __窗口__; }
QTabBar::tab {
    background: __面板__; color: __次要文本__;
    padding: 8px 18px; margin-right: 2px;
    border-top-left-radius: 8px; border-top-right-radius: 8px;
    font-size: 13px;
}
QTabBar::tab:selected {
    background: __编辑器__; color: __文本__;
    border-bottom: 2px solid __强调__;
}
QTabBar::tab:hover:!selected { background: __悬停__; color: __文本__; }
QTabBar::close-button {
    image: none; subcontrol-position: right;
}

/* 编辑器 */
QPlainTextEdit, QTextEdit {
    background: __编辑器__; color: __文本__;
    border: none; padding: 6px 0px;
    selection-background-color: __选区__; selection-color: __文本__;
}
QPlainTextEdit#console, QTextEdit#console {
    background: __控制台底__; color: __控制台字__;
    selection-background-color: __选区__;
}

/* 滚动条 */
QScrollBar:vertical {
    background: transparent; width: 12px; margin: 0px;
}
QScrollBar::handle:vertical {
    background: __悬停__; border-radius: 6px; min-height: 30px; margin: 2px;
}
QScrollBar::handle:vertical:hover { background: __按下__; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal {
    background: transparent; height: 12px; margin: 0px;
}
QScrollBar::handle:horizontal {
    background: __悬停__; border-radius: 6px; min-width: 30px; margin: 2px;
}
QScrollBar::handle:horizontal:hover { background: __按下__; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }

/* 运行窗口 */
#runHeader { background: __面板__; border-top: 1px solid __边框__; }
#runTitle { color: __文本__; font-size: 12px; background: transparent; }
#runStatus { color: __次要文本__; font-size: 12px; background: transparent; }
#inputBox {
    background: __编辑器__; color: __文本__;
    border: 1px solid __边框__; border-radius: 6px;
    padding: 6px 10px; font-size: 13px;
}
#inputBox:focus { border: 1px solid __强调__; }

/* 左侧竖条 */
#leftRail {
    background: {窗口}; border-right: 1px solid {边框};
}
#railBtn {
    color: {次要文本}; background: transparent;
    font-size: 16px; border-radius: 8px;
}
#railBtn:hover { background: {悬停}; color: {文本}; }
#railBtn:checked { background: {悬停}; color: {强调}; }

/* 顶部单行（新 UI 合并式） */
#topRow { background: {窗口}; border-bottom: 1px solid {边框}; }
#projectName { color: {文本}; font-size: 13px; background: transparent; }
#topBtn {
    color: {文本}; background: transparent;
    padding: 5px 10px; border-radius: 6px; font-size: 13px;
}
#topBtn:hover { background: {悬停}; }
#runBtn {
    color: {成功}; background: transparent;
    padding: 4px 8px; border-radius: 6px; font-size: 15px;
}
#runBtn:hover { background: {悬停}; }

/* 状态栏 */
#statusBar { background: __面板__; border-top: 1px solid __边框__; }
#statusLeft, #statusRight { color: __次要文本__; font-size: 11px; background: transparent; }

/* 菜单 */
QMenu {
    background: __浮层__; color: __文本__;
    border: 1px solid __边框__; border-radius: 8px; padding: 6px;
}
QMenu::item { padding: 7px 28px 7px 18px; border-radius: 5px; }
QMenu::item:selected { background: __强调__; color: #FFFFFF; }
QMenu::separator { height: 1px; background: __边框__; margin: 5px 10px; }

/* 对话框 */
QDialog { background: __窗口__; }
QLineEdit {
    background: __编辑器__; color: __文本__;
    border: 1px solid __边框__; border-radius: 6px; padding: 6px 10px;
}
QLineEdit:focus { border: 1px solid __强调__; }
QPushButton {
    background: __悬停__; color: __文本__;
    border: none; border-radius: 6px; padding: 7px 18px; font-size: 13px;
}
QPushButton:hover { background: __按下__; }
QPushButton:default { background: __强调__; color: #FFFFFF; }
QPushButton:default:hover { background: #4A88DA; }
QCheckBox { color: __文本__; spacing: 8px; background: transparent; }
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 1px solid __边框__; border-radius: 4px; background: __编辑器__;
}
QCheckBox::indicator:checked { background: __强调__; border: 1px solid __强调__; }
QComboBox {
    background: __编辑器__; color: __文本__;
    border: 1px solid __边框__; border-radius: 6px; padding: 5px 10px;
}
QComboBox QAbstractItemView {
    background: __浮层__; color: __文本__;
    border: 1px solid __边框__; selection-background-color: __强调__;
}
QListWidget {
    background: __面板__; color: __文本__; border: none; outline: none;
}
QListWidget::item { padding: 9px 14px; border-radius: 6px; }
QListWidget::item:selected { background: __选中行__; color: #FFFFFF; }
QListWidget::item:hover:!selected { background: __悬停__; }
QGroupBox { color: __文本__; border: none; margin-top: 8px; }
QLabel { background: transparent; }
QTabWidget::pane { border: none; background: __窗口__; }
"""


def 生成样式(主题=None, 字号=12):
    """把色表套进 QSS 模板，返回可直接 setStyleSheet 的字符串。

    QSS 里全是 CSS 的 `{}`，直接用 str.format 会冲突，
    所以模板里用的是 `__键名__` 占位符，这里用 replace 填充。
    """
    主题 = 主题 or 深色
    数据 = dict(主题)
    数据["界面字体"] = 界面字体
    数据["字号"] = str(字号)
    文本 = _QSS
    # 长的键先替换，避免 __窗口__ 被 __窗__ 之类误伤
    for 键 in sorted(数据, key=len, reverse=True):
        文本 = 文本.replace("__%s__" % 键, str(数据[键]))
    # Qt 的 QSS 解析器不认中文注释（会报 "Could not parse stylesheet"），
    # 所以模板里的注释只在源码里给人看，运行时一律剥掉。
    import re as _re

    文本 = _re.sub(r"/\*.*?\*/", "", 文本, flags=_re.S)
    return 文本


def 取主题(名, 备用=None):
    return 主题集.get(名) or 备用 or 深色


def 换主题(应用窗口, 主题, 字号=12):
    """给整个应用套上主题。一行搞定 —— 这就是维护性的提升。

    注意：务必传 QApplication 实例而不是主窗口，否则对话框等子窗口
    拿不到样式。若实际传入的是 QWidget，也能工作（样式会向下继承）。
    """
    应用窗口.setStyleSheet(生成样式(主题, 字号))
