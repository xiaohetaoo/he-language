# -*- coding: utf-8 -*-
"""核工坊 Qt 版完整功能自测。

覆盖：界面构建、文件操作、编辑功能、运行控制、主题、设置、配置持久化。
用法：python 测试/自测Qt.py
"""

import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.argv = [sys.argv[0]]

from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QKeyEvent, QTextCursor
from PySide6.QtWidgets import QApplication

import 核工坊Qt as gq
import 查找对话框
import 设置窗口Qt
import 配置

失败 = []


def 检查(条件, 说明):
    if 条件:
        print("  ok   %s" % 说明)
    else:
        print("  FAIL %s" % 说明)
        失败.append(说明)


def 主():
    应用 = QApplication(sys.argv)
    应用.setApplicationName("核工坊")
    目录 = tempfile.mkdtemp(prefix="核工坊Qt测试_")
    # 隔离配置：本测试会改字号/缩进/行号并写盘。若指向真实配置目录，
    # 跑一次就把用户的界面设置覆盖掉（曾经把制表宽留成 2）。
    os.environ["核工坊_配置目录"] = tempfile.mkdtemp(prefix="核工坊Qt配置_")

    print("[启动]")
    窗 = gq.主窗()
    窗.show()
    应用.processEvents()
    检查(窗.顶行 is not None, "自绘顶行")
    检查(len(窗.竖条.钮们) == 4, "左竖条 4 个按钮")
    检查(窗.标签栏.count() == 1, "初始一个标签")
    检查(窗.当前 is not None, "有当前文档")
    检查(窗.对照.toPlainText().strip() != "", "对照表已填充")

    print("[新建与编辑]")
    编 = 窗.当前
    编.置文本("核说（\"你好\"）\n")
    应用.processEvents()
    检查("核说" in 编.取文本(), "文本可写入")
    检查(编.blockCount() >= 2, "行数正确")

    print("[保存]")
    路径 = os.path.join(目录, "测试.xht")
    编.文件路径 = 路径
    检查(窗.保存(编), "保存成功")
    检查(os.path.exists(路径), "文件已写入")
    检查(not 编.已改, "保存后清除修改标记")

    print("[打开]")
    编2 = 窗.打开(路径)
    检查(编2 is 编, "重复打开同一文件会复用标签")
    检查(窗.标签栏.count() == 1, "标签数没变")
    检查(窗.打开(os.path.join(目录, "不存在.xht")) is None, "打开不存在文件安全返回")
    检查(窗.打开(目录) is None, "打开目录安全返回")

    print("[运行]")
    样例 = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "例子", "01_你好.xht",
    )
    if os.path.exists(样例):
        窗.打开(样例)
        应用.processEvents()
        窗.运行()
        截止 = time.time() + 15
        while time.time() < 截止:
            应用.processEvents()
            time.sleep(0.02)
            if 窗.进程 is None:
                break
        台 = 窗.控制台.toPlainText()
        检查("你好世界" in 台, "控制台有程序输出")
        检查("返回 0" in 台, "结束码 0")

    print("[停止]")
    慢 = os.path.join(目录, "慢.xht")
    with open(慢, "w", encoding="utf-8") as f:
        f.write('核导入 time\n核用 i 遍历 核数列（100）:\n    核说（i）\n    time.sleep（0.5）\n')
    窗.打开(慢)
    应用.processEvents()
    窗.运行()
    for _ in range(60):
        应用.processEvents()
        time.sleep(0.02)
    检查(窗.进程 is not None, "程序在运行")
    窗.停止()
    for _ in range(40):
        应用.processEvents()
        time.sleep(0.02)
    检查(窗.进程 is None, "停止后进程已清理")
    检查("[已停止]" in 窗.控制台.toPlainText(), "控制台显示已停止")

    print("[编辑功能]")
    编3 = 窗.新建()
    编3.置文本("x = 1\ny = 2\n")
    应用.processEvents()
    游 = 编3.textCursor()
    游.movePosition(QTextCursor.Start)
    游.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
    编3.setTextCursor(游)
    编3.切换注释()
    应用.processEvents()
    检查(编3.取文本().startswith("核核 "), "注释切换生效")
    编3.切换注释()
    应用.processEvents()
    检查(not 编3.取文本().startswith("核核 "), "取消注释生效")

    print("[自动缩进]")
    编3.置文本("核若 核对：")
    游 = 编3.textCursor()
    游.movePosition(QTextCursor.End)
    编3.setTextCursor(游)
    编3.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier))
    应用.processEvents()
    行 = 编3.取文本().splitlines()
    缩进 = len(行[-1]) - len(行[-1].lstrip()) if 行 else 0
    # 断言的是「等于当前制表宽」，不写死 4：用户在设置里把缩进改成 2
    # 之后，程序行为是对的，写死 4 反而误报。
    检查(缩进 == 编3.制表宽,
         "冒号后自动缩进 %d 空格（应等于制表宽 %d）" % (缩进, 编3.制表宽))

    print("[查找替换]")
    编3.置文本("甲\n乙\n甲\n")
    检查(编3.查找下一个("甲"), "查找命中")
    检查(编3.全部替换("甲", "丁") == 2, "全部替换 2 处")
    检查(编3.跳到行(2), "跳到第 2 行")
    检查(编3.当前行列()[0] == 2, "当前行号正确")

    print("[主题切换]")
    窗.换主题("浅色")
    应用.processEvents()
    检查(窗.主题名 == "浅色", "切到浅色")
    检查("#F7F8FA" in 窗.styleSheet() or "F7F8FA" in 窗.styleSheet(), "样式表已更新")
    窗.换主题("深色")
    应用.processEvents()
    检查(窗.主题名 == "深色", "切回深色")

    print("[面板开关]")
    窗.切换项目栏()
    应用.processEvents()
    检查(not 窗.项目框.isVisible(), "项目栏已隐藏")
    窗.切换项目栏()
    应用.processEvents()
    检查(窗.项目框.isVisible(), "项目栏已恢复")

    print("[设置窗口]")
    d = 设置窗口Qt.设置对话框(窗)
    检查(d.左栏.count() == 4, "设置四个分类")
    检查(d.栈.count() == 4, "设置四页")
    原 = 窗.主题名
    d._换主题("浅色" if 原 == "深色" else "深色")
    应用.processEvents()
    检查(窗.主题名 != 原, "设置内切主题即时生效")
    d.取消()
    应用.processEvents()
    检查(窗.主题名 == 原, "取消后主题还原")

    # 当前字号/缩进值必须能在下拉框里找到。曾经列表只写 (9,10,...,22) 这几个
    # 跳档值，而「改字号」是逐 1 加减、能到 15/17/19/21，findData 就返回 -1，
    # 下拉框显示成 9 pt，用户一按确定字号被悄悄改回 9。
    print("[设置项如实反映当前值]")
    原字号, 原缩进 = 窗.字号, 窗.制表宽
    窗.字号 = 15
    d2 = 设置窗口Qt.设置对话框(窗)
    应用.processEvents()
    检查(d2.字号框.currentData() == 15, "字号 15 能如实显示（不是回落到 9）")
    窗.制表宽 = 3
    d3 = 设置窗口Qt.设置对话框(窗)
    应用.processEvents()
    检查(d3.缩进框.currentData() == 3, "缩进 3 空格能如实显示（不是回落到 2）")
    d3.取消()
    应用.processEvents()
    窗.字号, 窗.制表宽 = 原字号, 原缩进

    print("[配置持久化]")
    窗.字号 = 15
    窗.存配置()
    import 配置

    cfg = 配置.读配置()
    检查(cfg.get("字号") == 15, "字号已写入配置")
    检查("项目目录" in cfg, "项目目录已记录")

    print("[正文不被行号遮挡]")
    # 用户报「第一行的核核被挡住了」：根因是 viewportMargins 算成 0，
    # 正文画到了行号栏下面。这里守住两条：
    #   1) 左边距必须等于行号区宽度
    #   2) 正文首个文字像素必须落在行号区右边界之外
    _样例 = "核核 这是第一行的注释\n数字们 = 核列表()\n"
    窗.当前.setPlainText(_样例)
    应用.processEvents()
    for _ in range(6):
        应用.processEvents()
    _编 = 窗.当前
    _编.重设行号边距()
    for _ in range(4):
        应用.processEvents()
    检查(
        _编.viewportMargins().left() == _编.行号.宽度,
        "左边距(%d) == 行号区宽度(%d)" % (_编.viewportMargins().left(), _编.行号.宽度),
    )
    _图 = _编.grab().toImage()
    _倍 = _图.width() / max(1, _编.width())
    _栏右 = int((_编.行号.geometry().x() + _编.行号.width()) * _倍)
    _底色 = (0x1E1F22, 0x2B2D30, 0xF7F8FA, 0xFFFFFF)

    def _找首文():
        # 扫多个 y：只扫固定的 y=10 会偶发失败 —— 首行块的位置随字体度量
        # 和首帧渲染时机略有变化（实测块 top=4，文字落在 y≈15~30）。
        # 扫一段高度内的任意一行，只要有一点文字像素就算找到。
        _图2 = _编.grab().toImage()
        for _yy in (10, 16, 20, 26, 32, 40, 46):
            _y2 = min(_图2.height() - 1, int(_yy * _倍))
            for _x in range(_栏右, min(_图2.width(), _栏右 + 260)):
                if (_图2.pixel(_x, _y2) & 0xFFFFFF) not in _底色:
                    return _x, _yy
        return None, None

    _首文 = None
    for _重试 in range(5):
        _首文, _命中y = _找首文()
        if _首文 is not None:
            break
        for _ in range(4):
            应用.processEvents()
    检查(
        _首文 is not None and _首文 >= _栏右,
        "第一行正文起点(%s @y=%s) 在行号栏右侧(%d)"
        % (_首文, _命中y if _首文 else "-", _栏右),
    )

    print("[自动缩进不叠加]")
    # QPlainTextEdit 原生回车不继承缩进，我们自己补；
    # 若补两次会 4→8→12 叠上去，看起来像「每行多吞了空格」。
    _编.置文本("")
    应用.processEvents()
    _编.setPlainText("核若 核对：")
    应用.processEvents()
    _游 = _编.textCursor()
    _游.movePosition(_游.MoveOperation.End)
    _编.setTextCursor(_游)
    _编.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier, "\r"))
    应用.processEvents()
    _缩 = len(_编.document().findBlockByNumber(1).text()) - len(
        _编.document().findBlockByNumber(1).text().lstrip()
    )
    检查(_缩 == _编.制表宽, "冒号回车后缩进 %d（应等于制表宽 %d，不是叠加成 8）" % (_缩, _编.制表宽))

    print("[图标区分度]")
    # 用户反馈「功能图标太像了，没有区分度」：改成自绘形状 + 各自颜色，
    # 这里锁住「每个按钮都有图，且两两不同」。
    图们 = {}
    for 键, 钮 in 窗.竖条.钮们.items():
        pm = 钮.pixmap()
        检查(not pm.isNull(), "%s 按钮有图标" % 键)
        图们[键] = pm.toImage()
    键们 = sorted(图们)
    相同对 = []
    for i in range(len(键们)):
        for j in range(i + 1, len(键们)):
            if 图们[键们[i]] == 图们[键们[j]]:
                相同对.append((键们[i], 键们[j]))
    检查(not 相同对, "竖条图标两两不同" + ("（重复：%s）" % 相同对 if 相同对 else ""))

    print("[设置入口唯一]")
    from PySide6.QtWidgets import QLabel as _QL

    顶行钮提示 = [c.toolTip() for c in 窗.顶行.findChildren(_QL)]
    检查(
        not any("设置" in t for t in 顶行钮提示),
        "顶行不再重复放设置入口",
    )
    检查("设置" in 窗.竖条.钮们, "竖条保留唯一设置入口")

    print("[输入不吞字]")
    import inspect

    import 编辑器 as _编辑器

    变化源 = inspect.getsource(_编辑器.编辑器._文本变化)
    # 只看真正的调用（docstring 里提到这两个名字是刻意写下的教训，不算）
    检查("self.主窗.更新状态栏(" not in 变化源, "文本变化里不再同步刷状态栏")
    检查("self.主窗._刷新标题(" not in 变化源, "文本变化里不再同步改标题")
    补记源 = inspect.getsource(_编辑器.编辑器._补记已改)
    检查("更新状态栏" in 补记源, "延后刷新里确实刷状态栏")
    检查(hasattr(窗.当前, "_界面刷新任务"), "编辑器有去抖定时器")
    键源 = inspect.getsource(_编辑器.编辑器.keyPressEvent)
    检查("_输入法组字中" in 键源, "自动配对给输入法让路")

    print("[配色对比度]")
    import 主题 as _主题

    def _亮(色):
        色 = 色.lstrip("#")
        值 = [int(色[i : i + 2], 16) / 255 for i in (0, 2, 4)]
        值 = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in 值]
        return 0.2126 * 值[0] + 0.7152 * 值[1] + 0.0722 * 值[2]

    def _比(前, 后):
        高, 低 = sorted([_亮(前), _亮(后)], reverse=True)
        return (高 + 0.05) / (低 + 0.05)

    for 名 in ("深色", "浅色"):
        表 = _主题.取主题(名)
        底 = 表["编辑器"]
        for 键 in ("文本", "次要文本", "行号字", "注释"):
            值 = _比(表[键], 底)
            检查(值 >= 4.5, "%s %s 对比度 %.2f ≥ 4.5" % (名, 键, 值))

    print("[行号与正文逐行对齐]")
    # 用户报「行标是歪的」。根因：blockBoundingGeometry 给的是内容坐标，
    # 加 contentOffset() 是**视口坐标**，上一版又减了一次行号栏自己的 y()，
    # 等于整体上移 6px。这里逐行量：行号该画的位置 == 光标所在的 y。
    _编2 = 窗.当前
    _编2.设行号(True)
    _编2.置文本("第一行\n第二行\n第三行\n第四行\n第五行\n")
    应用.processEvents()
    for _ in range(6):
        应用.processEvents()
    _视口 = _编2.viewport()
    _块 = _编2.firstVisibleBlock()
    _对齐差 = []
    for _i in range(5):
        _游 = QTextCursor(_块)
        _游.movePosition(QTextCursor.StartOfBlock)
        _光标顶 = _编2.cursorRect(_游).top()
        _应 = (_视口.mapToGlobal(QPoint(0, _光标顶)).y()
               - _编2.行号.mapToGlobal(QPoint(0, 0)).y())
        if abs(_应 - _光标顶) > 1:
            _对齐差.append((_i + 1, _光标顶, _应))
        _块 = _块.next()
    检查(not _对齐差, "五行行号与正文对齐" + ("（偏差：%s）" % _对齐差 if _对齐差 else ""))

    print("[缩进线不压正文]")
    # 缩进 1 级的行不该画线：线画在 x=16，正文从 x=19 起，只差 3px，
    # 看起来就像行首多了一个竖线字符。
    import inspect as _inspect

    import 编辑器 as _E

    _线源 = _inspect.getsource(_E.编辑器._画缩进线)
    检查("range(1, 级)" in _线源 and "range(1, 级 + 1)" not in _线源,
         "缩进线只画外层层级")

    print("[最大化不留圆角缺口]")
    # 用户报「全屏没占满」：窗口矩形其实精确等于屏幕可用区，
    # 缺的是四角 —— #rootFrame 的圆角在最大化时仍在，切掉了四个角。
    _窗 = 窗
    _窗.showMaximized()
    应用.processEvents()
    for _ in range(20):
        应用.processEvents()
    _图 = _窗.grab().toImage()
    _w, _h = _图.width(), _图.height()
    _底 = _窗.主题["窗口"].lower()
    _角色 = {_图.pixelColor(x, y).name().lower() for x, y in
             ((0, 0), (_w - 1, 0), (0, _h - 1), (_w - 1, _h - 1))}
    检查(_角色 == {_底}, "最大化四角都是窗口底色 %s（实际 %s）" % (_底, _角色))
    # grab() 的总会把圆角区填成底色，上面那条恒真、没有检测力。
    # 真正有用的是这两条：QSS 属性必须真的存住（否则规则永远不匹配），
    # 以及最大化时 DWM 必须收到「不圆角」。
    检查(_窗.外框.property("窗态") == "最大化",
         "最大化时 QSS 属性 窗态=最大化（实际 %r）" % _窗.外框.property("窗态"))
    # 属性名必须避开 QWidget 内建属性：用 "maximized" 会被 setProperty
    # 静默吞掉，读回来永远 False，QSS 规则从未匹配过。
    检查(_窗.外框.property("maximized") is False,
         "内建属性 maximized 不可用于自定义状态（记录这个坑）")
    try:
        import ctypes
        import ctypes.wintypes as _wt

        _dwm = ctypes.WinDLL("dwmapi")
        _v = _wt.DWORD()
        _dwm.DwmGetWindowAttribute(int(_窗.winId()), 33, ctypes.byref(_v),
                                  ctypes.sizeof(_v))
        检查(_v.value == 1, "最大化时 DWM 圆角偏好=1 不圆角（实际 %d）" % _v.value)
    except Exception as _e:  # noqa: BLE001
        print("  (跳过 DWM 检查：%s)" % _e)
    _窗.showNormal()
    应用.processEvents()
    for _ in range(8):
        应用.processEvents()
    检查(_窗.外框.property("窗态") == "已还原",
         "还原后 QSS 属性 窗态=已还原（实际 %r）" % _窗.外框.property("窗态"))

    print("[设置即时生效、无需重启]")
    # 用户报「设置应用不能马上生效，必须重启软件」。
    # 四个开关逐个验证：主窗属性 + 编辑器实际状态都要当场变。
    _窗.设行号(True)
    _窗.设缩进线(True)
    _窗.设制表宽(4)
    _窗.设自动高亮(True)
    _窗.设字号(12)
    应用.processEvents()
    _框 = 设置窗口Qt.设置对话框(_窗)
    _编S = _窗.当前

    _框.勾行号.setChecked(False)
    应用.processEvents()
    检查((not _窗.显示行号) and (not _编S.行号.isVisible())
          and _编S._行号隐藏, "关行号当场生效")
    _框.勾行号.setChecked(True)
    应用.processEvents()
    检查(_窗.显示行号 and _编S.行号.isVisible(), "开行号当场生效")

    _框.勾缩进线.setChecked(False)
    应用.processEvents()
    检查((not _窗.显示缩进线) and (not _编S._缩进线开), "关缩进线当场生效")

    _框.缩进框.setCurrentIndex(_框.缩进框.findData(2))
    应用.processEvents()
    检查(_窗.制表宽 == 2 and _编S.制表宽 == 2, "改制表宽当场生效")

    # 这个勾选框曾经根本没连信号，点了什么也不发生
    _框.勾高亮.setChecked(False)
    应用.processEvents()
    检查(_窗.自动高亮 is False and _编S.高亮.开 is False, "关自动高亮当场生效")
    _框.勾高亮.setChecked(True)
    应用.processEvents()
    检查(_窗.自动高亮 is True and _编S.高亮.开 is True, "开自动高亮当场生效")

    _框.字号框.setCurrentIndex(_框.字号框.findData(16))
    应用.processEvents()
    检查(_窗.字号 == 16 and _编S.字号 == 16, "改字号当场生效")

    # 「应用」必须写盘（以前只喊一句「已应用」，什么都不存）
    _框.应用()
    应用.processEvents()
    _盘 = 配置.读配置()
    检查(_盘.get("字号") == 16 and _盘.get("制表宽") == 2
          and _盘.get("行号") is True and _盘.get("缩进线") is False,
         "按应用后设置已写盘")

    # 「取消」必须每一项都还原（以前只还原主题和字号）
    _框2 = 设置窗口Qt.设置对话框(_窗)
    _框2.缩进框.setCurrentIndex(_框2.缩进框.findData(8))
    _框2.勾高亮.setChecked(False)
    _框2.字号框.setCurrentIndex(_框2.字号框.findData(10))
    应用.processEvents()
    _框2.取消()
    应用.processEvents()
    检查(_窗.制表宽 == 2 and _窗.自动高亮 is True and _窗.字号 == 16,
         "取消后每一项都还原")

    # 收尾：恢复正常值，后面的测试按默认制表宽走
    _窗.设制表宽(4)
    _窗.设字号(12)
    _窗.设行号(True)
    _窗.设缩进线(True)
    _窗.设自动高亮(True)
    应用.processEvents()

    print("[无边框窗口可拖边缩放]")
    # FramelessWindowHint 的窗口系统不会给边缘缩放，得自己调
    # startSystemResize。否则用户会觉得「窗口尺寸锁死了」。
    _窗3 = 窗
    _窗3.resize(1100, 760)
    应用.processEvents()
    _w3, _h3 = _窗3.width(), _窗3.height()
    _检查边 = [
        ("左", (0, _h3 // 2), Qt.LeftEdge),
        ("右", (_w3 - 1, _h3 // 2), Qt.RightEdge),
        ("上", (_w3 // 2, 0), Qt.TopEdge),
        ("下", (_w3 // 2, _h3 - 1), Qt.BottomEdge),
    ]
    _边错 = []
    for _名, (_x, _y), _望 in _检查边:
        _得 = _窗3._落在边缘(_窗3.mapToGlobal(QPoint(_x, _y)))
        if _得 != _望:
            _边错.append((_名, _得, _望))
    检查(not _边错, "四边都能识别为可缩放边缘" + ("（%s）" % _边错 if _边错 else ""))
    # 边缘内 20px 不该被当成边缘，否则会抢掉正常点击
    检查(_窗3._落在边缘(_窗3.mapToGlobal(QPoint(20, _h3 // 2))) is None,
         "离边 20px 不误判为边缘")
    # 光标要跟着边变，否则看不出能拖
    检查(gq.主窗._边缘光标(Qt.LeftEdge) == Qt.SizeHorCursor,
         "左右边是水平缩放光标")
    检查(gq.主窗._边缘光标(Qt.TopEdge) == Qt.SizeVerCursor,
         "上下边是垂直缩放光标")
    检查(gq.主窗._边缘光标(Qt.LeftEdge | Qt.TopEdge) == Qt.SizeFDiagCursor,
         "左上角是对角缩放光标")

    print("[关闭文档]")
    for 文档 in list(窗.文档集):
        文档.已改 = False
        窗.关闭文档(文档, 强制=True)
    应用.processEvents()
    检查(len(窗.文档集) == 0, "全部关闭")
    检查(窗.标签栏.count() == 0, "标签已清空")

    窗.停止(静默=True)
    窗.close()

    import shutil

    shutil.rmtree(目录, ignore_errors=True)
    print()
    if 失败:
        print("失败 %d 项：" % len(失败))
        for 项 in 失败:
            print("  - %s" % 项)
        return 1
    print("Qt 版功能自测全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(主())
