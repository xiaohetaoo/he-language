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

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent, QTextCursor
from PySide6.QtWidgets import QApplication

import 核工坊Qt as gq
import 查找对话框
import 设置窗口Qt

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
    检查(缩进 == 4, "冒号后自动缩进 4 空格（实际 %d）" % 缩进)

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
