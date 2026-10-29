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
    # 实心按钮/菜单选中项：底色要比「强调」再深一点，白字才能到 4.5
    "按钮底": "#2F6AE0",
    "按钮热": "#3570E4",
    "悬停": "#393B40",
    "按下": "#43454A",
    "选中行": "#2E436E",
    "错误": "#FF6B7A",
    "警告": "#D5B778",
    "成功": "#6AAB73",
    "关闭红": "#C42B1C",
    # 图标：每个功能一个颜色。这里的取值都验算过，
    # 保证在各自的底色（窗口/悬停）上对比度 ≥ 3.0（WCAG 非文本对比）。
    "图标项目": "#6C9EF8",
    "图标结构": "#B58EF8",
    "图标运行": "#4CAF6E",
    "图标设置": "#9AA0AB",
    "图标状态点": "#6AAB73",
    # 控制台
    "控制台底": "#1E1F22",
    "控制台字": "#BCBEC4",
    # 版本控制面板的 diff 预览：增行 / 删行 的底色与字色。
    # 底色刻意很淡（在 darcula 的 #1E1F22 上几乎只是「泛一点绿/红」），
    # 因为整屏都是色块会盖过代码本身；靠左边的 +/− 符号和淡底色一起区分。
    "diff增底": "#243A2B",
    "diff删底": "#3D2528",
    "diff增字": "#8FD4A0",
    "diff删字": "#F09AA5",
    "diff头字": "#7FB3F0",
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
    "行号字": "#676D76",
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
    "按钮底": "#2F6AE0",
    "按钮热": "#3570E4",
    "悬停": "#E6E9ED",
    "按下": "#D8DCE2",
    "选中行": "#D5E5FF",
    "错误": "#C7221F",
    "警告": "#8A6D00",
    "成功": "#067D17",
    "关闭红": "#C42B1C",
    # 图标：浅色底上必须用更深的同色系，否则亮蓝亮绿会糊在白底上
    "图标项目": "#2F6FD0",
    "图标结构": "#7B4FD0",
    "图标运行": "#2E8B57",
    "图标设置": "#5F6672",
    "图标状态点": "#067D17",
    "控制台底": "#FFFFFF",
    "控制台字": "#3A3F45",
    # diff 增/删行。浅色底上要比深色主题更实一点，
    # 否则白底上的淡绿淡红基本看不出来。
    "diff增底": "#E6F5EA",
    "diff删底": "#FBE9EC",
    "diff增字": "#1A7F37",
    "diff删字": "#B4232C",
    "diff头字": "#2F6FD0",
}

主题集 = {"深色": 深色, "浅色": 浅色}

#: 等宽字体候选（按优先级）
等宽候选 = ("Cascadia Mono", "JetBrains Mono", "Consolas", "Courier New")
#: 界面字体
界面字体 = "Microsoft YaHei UI"

#: 编辑器字号范围与步长 —— **唯一来源**。
#: 主窗、设置窗口、自检都必须读这里，别再各写一份 min/max：
#: 以前三处各写各的（9~22 / 9~23 / 8~28），改一处就会出现
#: 「设置里能调到 22、按 +/- 只能到 22、配置里却存了 26」这种不一致。
字号最小 = 8
字号最大 = 40
字号步长 = 1


def 夹字号(字号):
    """把任意字号夹到允许范围内（并取整）。"""
    try:
        n = int(round(float(字号)))
    except (TypeError, ValueError):
        return 12
    return max(字号最小, min(字号最大, n))


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
/* 编辑器字号来自设置里的「字号」。
   QSS 的 font-size 优先级高于 setFont()，原来这里写死 13px，
   于是 编辑器.设置字体() 里设的 QPointSize 被完全覆盖 ——
   用户改字号什么都没发生（实测 QFont.pointSize() 恒为 -1、
   fontMetrics 高度恒为 16）。用 __字号__ 占位符把设置接进来。 */
QPlainTextEdit, QTextEdit {
    font-family: "__等宽字体__";
    font-size: __字号__px;
}
/* 行号栏自己也是 QWidget 子类，会被上面 QWidget 的 font-size:13px 覆盖，
   导致正文字号变了、行号数字却不变（看起来像行号突然变小）。
   这里显式给它同样的字号与等宽字体。 */
#gutter {
    font-family: "__等宽字体__";
    font-size: __字号__px;
}
QMainWindow { background: __窗口__; }
QToolTip {
    background: __浮层__; color: __文本__;
    border: 1px solid __边框__; border-radius: 6px; padding: 5px 8px;
}

/* 外框（圆角无边框窗口）。
   最大化时必须把圆角去掉：#rootFrame 的四角会被切掉一小块，
   屏幕四角因此露出桌面/阴影，看起来就像「全屏没占满」。
   主窗._应用窗口外观() 通过设置 maximized 属性切换下面这条规则。

   注意：属性名不能叫 maximized —— 那是 QWidget 的内建只读属性，
   setProperty("maximized", ...) 会被直接吞掉（读回来永远是 False，
   dynamicPropertyNames 里也看不到），这条规则就永远不会匹配。
   用 窗态 这个名字，中文名不会被内建属性占用。 */
#rootFrame {
    background: __窗口__;
    border: 1px solid __边框__;
    border-radius: 12px;
}
#rootFrame[窗态="最大化"] {
    border-radius: 0px;
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

/* 品牌字样（标志旁边那个「核工坊」） */
#品牌字 {
    color: __文本__; font-size: 14px; font-weight: bold;
    background: transparent; padding: 2px 4px; border-radius: 6px;
}
#品牌字:hover { background: __悬停__; }

/* 窗口按钮。
   objectName 必须和代码里一致：窗口钮 / 关闭钮。
   以前这里写的是 #winBtn / #closeBtn，和代码对不上，于是三个窗口按钮
   一条样式都没套上 —— 没有悬停反馈、关闭钮也不会变红。 */
#窗口钮 {
    color: __次要文本__; font-size: 13px;
    background: transparent; padding: 0px;
}
#窗口钮:hover { background: __悬停__; color: __文本__; }
#关闭钮 { color: __次要文本__; background: transparent; }
#关闭钮:hover { background: __关闭红__; color: #FFFFFF; }

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
    /* padding 的左右必须是 0：行号栏的宽度由 setViewportMargins 精确预留，
       这里再给左右 padding 会把文字又往里推（或覆盖掉视口左边距，
       导致文字贴到最左边、和行号重叠，看起来就像每行开头被切掉了）。 */
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
    background: __窗口__; border-right: 1px solid __边框__;
}
#railBtn {
    color: __次要文本__; background: transparent;
    font-size: 16px; border-radius: 8px;
}
#railBtn:hover { background: __悬停__; color: __文本__; }
#railBtn:checked { background: __悬停__; color: __强调__; }

/* 顶部单行（新 UI 合并式） */
#topRow { background: __窗口__; border-bottom: 1px solid __边框__; }
#projectName { color: __文本__; font-size: 13px; background: transparent; }
#topBtn {
    color: __文本__; background: transparent;
    padding: 5px 10px; border-radius: 6px; font-size: 13px;
}
#topBtn:hover { background: __悬停__; color: __文本__; }
#runBtn {
    color: __成功__; background: transparent;
    padding: 4px 8px; border-radius: 6px; font-size: 15px;
}
#runBtn:hover { background: __悬停__; }

/* 状态栏 */
#statusBar { background: __面板__; border-top: 1px solid __边框__; }
#statusLeft, #statusRight { color: __次要文本__; font-size: 11px; background: transparent; }

/* 菜单 */
QMenu {
    background: __浮层__; color: __文本__;
    border: 1px solid __边框__; border-radius: 8px; padding: 6px;
}
QMenu::item { padding: 7px 28px 7px 18px; border-radius: 5px; }
QMenu::item:selected { background: __按钮底__; color: #FFFFFF; }
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
/* 主按钮（确定 / 运行 等）。
   用自定义属性 primary="true" 而不是 :default —— Qt 会在对话框显示时
   把「默认按钮」偷偷转给焦点链里第一个 autoDefault 的按钮，
   :default 因此会飘到不相关的按钮上（实测「更改…」变成蓝色，
   按回车还会弹文件选择框而不是确认）。属性由我们自己控制，不会被抢。 */
QPushButton[primary="true"] {
    background: __按钮底__; color: #FFFFFF;
}
QPushButton[primary="true"]:hover { background: __按钮热__; }
QPushButton:default { background: __按钮底__; color: #FFFFFF; }
QPushButton:default:hover { background: __按钮热__; }
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
/* 下拉箭头区。不写这两条的话，Qt 会用 Fusion 样式的默认值：
   箭头那边带一块更亮的底 + 一条竖分隔线，在深色主题上很扎眼。 */
QComboBox::drop-down {
    subcontrol-origin: padding; subcontrol-position: center right;
    width: 20px; border: none; background: transparent;
}
/* 箭头由程序自绘（见 核工坊Qt.带箭头下拉框）。
   Qt 的 QSS 不支持 CSS 的「边框拼三角形」写法，写了会渲染成一个实心方块；
   而图片在单文件打包后相对路径容易失效。自绘最稳。 */
QComboBox::down-arrow { width: 0px; height: 0px; image: none; }
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

/* 设置窗口内部用的几个文字角色。
   以前这些控件的颜色是靠 setStyleSheet(f"color: {主题[文本]}") 行内写死的，
   换主题时不会更新 —— 从深色切到浅色后，标题会保持深色主题的浅灰，
   在浅底上几乎看不见（实测「外观 / 配色 / 编辑器字号」全糊成一片）。
   改走 QSS 之后，换主题重生成样式表就自动跟着变。 */
#pageTitle { color: __文本__; font-size: 17px; font-weight: bold; background: transparent; }
#groupTitle { color: __文本__; font-weight: bold; background: transparent; }
#hintText  { color: __次要文本__; font-size: 11px; background: transparent; }
#sliderValue { color: __文本__; font-weight: bold; background: transparent; }
#aboutTitle { color: __文本__; font-size: 15px; font-weight: bold; background: transparent; }
#linkLabel  { color: __强调__; background: transparent; }
/* 版本控制面板里的 diff 预览。
   diff 是「只读的代码」，所以走编辑器的底色与等宽字体，
   再加一条左边框把它和上面的文件列表分开。 */
#diffView {
    background: __编辑器__;
    color: __次要文本__;
    border: 1px solid __边框__;
    border-radius: 6px;
    padding: 6px 8px;
    font-family: "__等宽字体__";
}
QTabWidget::pane { border: none; background: __窗口__; }

/* 滑动条（设置里的字号）。
   Qt 的 QSlider 子控件尺寸规则很别扭：
     · handle 的高度 = groove 高度 + 2*|margin|，写负 margin 会把
       手柄拉成竖椭圆（实测 14x22，像颗胶囊而不是圆钮）；
     · 但 groove 高度太小（4px）时手柄根本没有画圆的空间。
   解法：把 groove 做到 16px 高（给手柄正方形空间），再用竖直渐变
   让「可见的轨道」只占中间那 4px —— 上下各 37.5% 都是透明的。 */
QSlider { min-height: 24px; }
QSlider::groove:horizontal {
    height: 16px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0    transparent,
        stop:0.37 transparent,
        stop:0.38 __边框__,
        stop:0.62 __边框__,
        stop:0.63 transparent,
        stop:1    transparent);
}
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0    transparent,
        stop:0.37 transparent,
        stop:0.38 __强调__,
        stop:0.62 __强调__,
        stop:0.63 transparent,
        stop:1    transparent);
}
QSlider::add-page:horizontal { background: transparent; }
/* 圆钮：内容 8px + 边框 3px*2 = 14px 见方，半径 7 → 正圆。
   margin 归零，让高度等于 groove 的 16px 减去自身，不再被撑长。 */
QSlider::handle:horizontal {
    background: __强调__;
    border: 3px solid __编辑器__;
    width: 8px;
    height: 8px;
    margin: 1px 0px;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover { background: __按钮热__; }
QSlider::handle:horizontal:pressed { background: __按钮热__; }
QSlider::tick:horizontal { background: transparent; }
"""


def 生成样式(主题=None, 字号=12, 等宽=None):
    """把色表套进 QSS 模板，返回可直接 setStyleSheet 的字符串。

    QSS 里全是 CSS 的 `{}`，直接用 str.format 会冲突，
    所以模板里用的是 `__键名__` 占位符，这里用 replace 填充。

    `字号` 同时决定编辑器字号（QSS 的 font-size 优先级高于 setFont()，
    所以必须写进 QSS 才真的生效）。`等宽` 不传就用候选表第一项，
    真正可用性由调用方（编辑器.挑等宽字体）保证。
    """
    主题 = 主题 or 深色
    数据 = dict(主题)
    数据["界面字体"] = 界面字体
    数据["字号"] = str(int(字号))
    数据["等宽字体"] = 等宽 or 等宽候选[0]
    文本 = _QSS
    # 保险：模板里若混进了 `{中文名}` 这种单花括号写法（CSS 的块花括号
    # 里永远是选择器和声明，绝不会只有纯中文），先统一成 `__中文名__`。
    # 教训：曾经有 12 处用了 `{窗口}` 这类写法，替换逻辑只认 `__窗口__`，
    # 于是这些声明原样留在 QSS 里被 Qt 判为非法值而整条丢弃 ——
    # 顶栏、左侧竖条、运行按钮因此一直没有样式，表现为「图标和文字看不清」。
    import re as _re0

    文本 = _re0.sub(r"\{([\u4e00-\u9fff]+)\}", r"__\1__", 文本)
    # 长的键先替换，避免 __窗口__ 被 __窗__ 之类误伤
    for 键 in sorted(数据, key=len, reverse=True):
        文本 = 文本.replace("__%s__" % 键, str(数据[键]))
    # Qt 的 QSS 解析器不认中文注释（会报 "Could not parse stylesheet"），
    # 所以模板里的注释只在源码里给人看，运行时一律剥掉。
    import re as _re

    文本 = _re.sub(r"/\*.*?\*/", "", 文本, flags=_re.S)
    # 兜底校验：不该再有残留占位符。
    # 注意别把 CSS 的块花括号当占位符 —— 只有「花括号里全是中文」
    # 或者「还剩 __某某__」才是真的没替换掉。
    残留 = _re.findall(r"\{[\u4e00-\u9fff]+\}", 文本) + _re.findall(r"__[^_\s{};]+__", 文本)
    if 残留:
        raise ValueError("QSS 模板有没被替换的占位符：%r" % 残留[:3])
    return 文本


def 取主题(名, 备用=None):
    return 主题集.get(名) or 备用 or 深色


def 换主题(应用窗口, 主题, 字号=12, 等宽=None):
    """给整个应用套上主题。一行搞定 —— 这就是维护性的提升。

    注意：务必传 QApplication 实例而不是主窗口，否则对话框等子窗口
    拿不到样式。若实际传入的是 QWidget，也能工作（样式会向下继承）。
    """
    应用窗口.setStyleSheet(生成样式(主题, 字号, 等宽))
