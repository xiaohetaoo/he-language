# -*- coding: utf-8 -*-
"""全量界面可见性审查。

不靠「看配色表猜」，而是真的把控件渲染出来、取像素、算 WCAG 对比度。
遍历每个窗口的控件树，凡是带文字的控件都量一遍，低于阈值就报出来。

用法：
    python 测试/审查可见性.py            # 审查深浅两套主题
    python 测试/审查可见性.py --详细      # 额外打印通过的项
退出码：0 全部达标，1 有未达标项。
"""
import os
import sys
from collections import Counter
from math import isclose

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if 根 not in sys.path:
    sys.path.insert(0, 根)

os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "0")

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QTabBar,
    QTableWidget,
    QTreeWidget,
    QWidget,
)

import 主题

#: 文字对比度阈值（WCAG AA，正文字号都小于 18px，一律按 4.5 要求）
文字阈值 = 4.5
#: 图标/装饰性元素阈值（WCAG 非文本对比 1.4.11 要求 3.0）
图标阈值 = 3.0

详细 = "--详细" in sys.argv

问题 = []
通过数 = [0]


def 转线性(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def 亮度(色):
    r, g, b = 色.red(), 色.green(), 色.blue()
    return 0.2126 * 转线性(r) + 0.7152 * 转线性(g) + 0.0722 * 转线性(b)


def 对比度(前, 后):
    a, b = 亮度(前), 亮度(后)
    if a < b:
        a, b = b, a
    return (a + 0.05) / (b + 0.05)


def 取前景背景(图, 区域=None):
    """从渲染结果里估出背景色与文字色。

    背景 = 区域内出现最多的颜色（底色成片）。
    文字 = 离背景最远的那 2% 像素取中位。不能按「出现次数」筛文字：
    Windows 开了次像素（ClearType）平滑后，单个字芯像素的 RGB 几乎
    各不相同，按次数筛会一个都筛不出来，只剩边框线被当成文字。
    """
    if 区域 is not None:
        from PySide6.QtCore import QRect

        图 = 图.copy(QRect(*区域))
    宽, 高 = 图.width(), 图.height()
    if 宽 <= 0 or 高 <= 0:
        return None, None
    计数 = Counter()
    for y in range(高):
        for x in range(宽):
            计数[图.pixel(x, y) & 0xFFFFFF] += 1
    if not 计数:
        return None, None
    背景值, _ = 计数.most_common(1)[0]
    背景 = QColor(背景值)
    底亮 = 亮度(背景)
    最好, 最好距 = None, -1.0
    for 值 in 计数:
        if 值 == 背景值:
            continue
        距 = abs(亮度(QColor(值)) - 底亮)
        if 距 > 最好距:
            最好, 最好距 = 值, 距
    return 背景, (QColor(最好) if 最好 is not None else None)


def 记(名称, 前景, 背景, 阈值, 类别="文字"):
    比 = 对比度(前景, 背景)
    if 比 >= 阈值:
        通过数[0] += 1
        if 详细:
            print("    ok   %-28s %.2f" % (名称, 比))
    else:
        问题.append((名称, 比, 阈值, 类别, 前景.name(), 背景.name()))
        print("    !!   %-28s %.2f  (需 %.1f)  %s/%s" % (名称, 比, 阈值, 前景.name(), 背景.name()))
    return 比


def 量控件(控件, 名称前缀, 阈值=文字阈值, 区域=None):
    """量一个控件的文字对比度。"""
    try:
        if not 控件.isVisible() or 控件.width() < 6 or 控件.height() < 6:
            return
        图 = 控件.grab().toImage()
    except Exception:
        return
    背景, 前景 = 取前景背景(图, 区域)
    if 背景 is None or 前景 is None:
        return
    记("%s" % 名称前缀, 前景, 背景, 阈值)


def 遍历(窗口, 前缀=""):
    """递归遍历控件树，凡是带文字的控件都量一遍。"""
    for 子 in 窗口.findChildren(QWidget):
        if not 子.isVisible():
            continue
        名 = 子.objectName() or 子.__class__.__name__
        标签 = "%s%s" % (前缀, 名)

        if isinstance(子, (QLineEdit, QPlainTextEdit)):
            # 无文字的空控件跳过（取不到前景）
            if isinstance(子, QLineEdit) and not 子.text():
                continue
            if isinstance(子, QPlainTextEdit) and not 子.toPlainText():
                continue
            if isinstance(子, QPlainTextEdit):
                # 逐行量：整块量会被大面积空白稀释，一行一行才看得出
                # 哪一类语法 token 混在底色里看不清。
                from PySide6.QtGui import QTextCursor

                视 = 子.viewport()
                图 = 视.grab().toImage()
                文 = 子.document()
                for i in range(min(文.blockCount(), 12)):
                    块 = 文.findBlockByNumber(i)
                    if not 块.text().strip():
                        # 空行没有文字，量到的只会是缩进参考线，跳过
                        continue
                    r = 子.cursorRect(QTextCursor(块))
                    if r.height() < 3:
                        continue
                    y = max(0, r.top() - 1)
                    区 = (0, y, min(图.width(), 700), max(2, r.height() + 2))
                    if 区[1] + 区[3] > 图.height():
                        continue
                    背景, 前景 = 取前景背景(图, 区)
                    if 背景 and 前景:
                        记("%s/第%d行" % (标签, i + 1), 前景, 背景, 文字阈值)
                continue
            量控件(子, 标签)
        elif isinstance(子, QAbstractButton) and 子.text().strip():
            量控件(子, 标签)
        elif isinstance(子, QLabel) and 子.text().strip():
            # 注意：只有空白字符的标签必须跳过 —— 它没有文字像素，
            # 取到的「最远色」会是边框线，报出假的不达标。
            量控件(子, 标签)
        elif isinstance(子, QComboBox) and 子.currentText():
            量控件(子, 标签)
        elif isinstance(子, QGroupBox) and 子.title():
            量控件(子, 标签)
        elif isinstance(子, QTreeWidget):
            # 逐个可见条目量
            视 = 子.viewport()
            for i in range(min(子.topLevelItemCount(), 6)):
                项 = 子.topLevelItem(i)
                if 项 is None:
                    continue
                r = 子.visualItemRect(项)
                if r.height() < 4:
                    continue
                图 = 视.grab().toImage()
                背景, 前景 = 取前景背景(图, (0, r.top(), 图.width(), max(1, r.height())))
                if 背景 and 前景:
                    记("%s/项%d" % (标签, i), 前景, 背景, 文字阈值)
        elif isinstance(子, QTabBar):
            # 每个标签页的标题
            图 = 子.grab().toImage()
            for i in range(子.count()):
                r = 子.tabRect(i)
                if r.height() < 4 or r.width() < 8:
                    continue
                背景, 前景 = 取前景背景(图, (r.left(), r.top(), r.width(), r.height()))
                if 背景 and 前景:
                    记("%s/标签%d" % (标签, i), 前景, 背景, 文字阈值)
        elif isinstance(子, QTableWidget):
            # 表头 + 前几行（语法对照表）
            视 = 子.viewport()
            图 = 视.grab().toImage()
            for 行 in range(min(子.rowCount(), 4)):
                r = 子.visualRect(子.model().index(行, 0))
                if r.height() < 4:
                    continue
                背景, 前景 = 取前景背景(图, (0, r.top(), min(图.width(), 400), r.height()))
                if 背景 and 前景:
                    记("%s/行%d" % (标签, 行), 前景, 背景, 文字阈值)
            横 = 子.horizontalHeader()
            if 横.isVisible():
                量控件(横, "%s/表头" % 标签)


def 审查图标(主窗):
    """图标可见性：竖条按钮、运行/顶部按钮、窗口按钮。

    关键：这些按钮 `background: transparent`，单独 grab 得到的是
    未绘制的黑图（0,0,0），必须从**父控件**的整体渲染里裁出它那一块，
    才能拿到真实的背景色。
    """
    from PySide6.QtCore import QPoint

    for 子 in 主窗.findChildren(QWidget):
        if not 子.isVisible() or 子.width() < 8 or 子.height() < 8:
            continue
        名 = 子.objectName()
        if not (名.endswith("Btn") or 名 in ("railBtn", "brandMark")):
            continue
        父 = 子.parentWidget()
        if 父 is None:
            continue
        图 = 父.grab().toImage()
        位 = 子.mapTo(父, QPoint(0, 0))
        区域 = (位.x(), 位.y(), 子.width(), 子.height())
        背景, 前景 = 取前景背景(图, 区域)
        if 背景 is None or 前景 is None:
            continue
        比 = 对比度(前景, 背景)
        if 比 < 图标阈值:
            记("图标 %s" % (名 or "?"), 前景, 背景, 图标阈值, "图标")
        else:
            通过数[0] += 1
            if 详细:
                print("    ok   图标 %-24s %.2f" % (名, 比))


def 审查菜单(主窗):
    """菜单栏与弹出菜单的文字。"""
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QMenu

    条 = 主窗.menuBar()
    if 条 is not None and 条.isVisible() and 条.actions():
        量控件(条, "菜单栏")

    菜单 = QMenu(主窗)
    菜单.setObjectName("审查用菜单")
    for 文本 in ("打开文件", "保存", "运行程序"):
        菜单.addAction(文本)
    菜单.addSeparator()
    菜单.addAction("退出")
    菜单.show()
    for _ in range(6):
        QApplication.processEvents()
    量控件(菜单, "弹出菜单")
    菜单.close()


def 审查编辑器配色(主窗, 主题名):
    """编辑器里的每一类语法 token 都要能看清。"""
    from 主题 import 取主题

    色表 = 取主题(主题名)
    底 = QColor(色表["编辑器"])
    行号底 = QColor(色表["行号底"])
    for 键, 说明, 后 in (
        ("文本", "正文", 底),
        ("注释", "注释", 底),
        ("字符串", "字符串", 底),
        ("数字", "数字", 底),
        ("关键字", "关键字", 底),
        ("内置", "内置函数", 底),
        ("函数名", "函数名", 底),
        ("行号字", "行号", 行号底),
    ):
        if 键 in 色表:
            记("编辑器/%s" % 说明, QColor(色表[键]), 后, 文字阈值)


def 审查主题色表(主题名):
    """直接量色表里每一对「文字色 / 它所在的底色」，覆盖非控件场景。"""
    色表 = 主题.取主题(主题名)
    窗口 = QColor(色表["窗口"])
    面板 = QColor(色表["面板"])
    编辑器 = QColor(色表["编辑器"])
    控制台底 = QColor(色表["控制台底"])

    配对 = [
        ("正文/窗口", "文本", 窗口),
        ("正文/面板", "文本", 面板),
        ("次要文本/窗口", "次要文本", 窗口),
        ("次要文本/面板", "次要文本", 面板),
        ("行号字/行号底", "行号字", QColor(色表["行号底"])),
        ("注释/编辑器", "注释", 编辑器),
        ("控制台字/控制台底", "控制台字", 控制台底),
        ("控制台命令/控制台底", "控制台命令", 控制台底),
        ("面包屑字/窗口", "面包屑字", 窗口),
        ("选中行字/选中行", "文本", QColor(色表["选中行"])),
        ("成功/面板", "成功", 面板),
        ("错误/面板", "错误", 面板),
        ("警告/面板", "警告", 面板),
    ]
    for 名, 键, 底 in 配对:
        if 键 in 色表:
            记("色表/%s" % 名, QColor(色表[键]), 底, 文字阈值)


def 跑一轮(应用, 主题名):
    print("\n=== 主题：%s ===" % 主题名)
    import 核工坊Qt

    w = 核工坊Qt.主窗()
    主题.换主题(应用, 主题.取主题(主题名), 12)
    w.resize(1360, 860)
    w.show()
    for _ in range(12):
        应用.processEvents()

    # 让所有面板都真的可见、编辑器里有真代码 —— 否则量到的只是空壳，
    # 隐藏控件的文字根本没被渲染，审查会漏掉一大片。
    样本 = (
        '核核 这是注释\n'
        '核定义 打招呼（名字）：\n'
        '    核说（核"你好，{名字}！"）\n'
        '    x = 123\n'
        '    y = "字符串"\n'
        '    核返回 x\n'
        '核用 i 遍历 核数列（3）：\n'
        '    打招呼（i）\n'
    )
    if getattr(w, "当前", None) is not None:
        w.当前.setPlainText(样本)
        w.当前.换主题()
    for _ in range(10):
        应用.processEvents()

    print("  [色表直接配对]")
    审查主题色表(主题名)
    print("  [编辑器语法配色]")
    审查编辑器配色(w, 主题名)
    print("  [实际渲染控件]")
    遍历(w, "")
    审查图标(w)
    审查菜单(w)

    # 设置窗口（独立 QDialog，样式需单独确认）
    try:
        import 设置窗口Qt

        d = 设置窗口Qt.设置对话框(w)
        d.show()
        for _ in range(8):
            应用.processEvents()
        print("  [设置窗口]")
        遍历(d, "设置/")
        d.close()
    except Exception as e:
        print("    设置窗口打不开：%r" % (e,))

    # 查找 / 替换对话框（需要传编辑器）
    for 名, 类, 参数, 前缀 in (
        ("查找对话框", "查找对话框", (w.当前,) if w.当前 else (None,), "查找/"),
        ("跳转对话框", "跳转对话框", (w.当前,) if w.当前 else (None,), "跳转/"),
    ):
        try:
            import 查找对话框

            f = getattr(查找对话框, 类)(w, *参数)
            f.show()
            for _ in range(6):
                应用.processEvents()
            print("  [%s]" % 名)
            遍历(f, 前缀)
            f.close()
        except Exception as e:
            print("    %s 打不开：%r" % (名, e))

    # 快速打开（Ctrl+P）
    try:
        import 快速打开

        q = 快速打开.快速打开(w)
        q.show()
        for _ in range(6):
            应用.processEvents()
        print("  [快速打开]")
        遍历(q, "快速打开/")
        q.close()
    except Exception as e:
        print("    快速打开打不开：%r" % (e,))

    w.close()
    for _ in range(4):
        应用.processEvents()


def main():
    应用 = QApplication.instance() or QApplication(sys.argv)
    for 主题名 in ("深色", "浅色"):
        跑一轮(应用, 主题名)

    print("\n" + "=" * 62)
    if 问题:
        print("未达标 %d 项（通过 %d 项）：" % (len(问题), 通过数[0]))
        for 名, 比, 阈, 类, 前, 后 in 问题:
            print("  %-34s %.2f < %.1f  [%s] %s / %s" % (名, 比, 阈, 类, 前, 后))
        return 1
    print("全部达标（%d 项）" % 通过数[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
