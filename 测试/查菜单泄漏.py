# -*- coding: utf-8 -*-
"""QAction / QMenu 泄漏与菜单行为验证。

弹主菜单 每次都新建一批 QAction(名, self) —— 父对象是主窗，
菜单 exec 结束后没人 delete 它们，于是每开一次菜单就多一批。

用法：python 测试/查菜单泄漏.py
"""

import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("核工坊_配置目录", tempfile.mkdtemp(prefix="核工坊菜单_"))

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication  # noqa: E402
from PySide6.QtGui import QAction  # noqa: E402

import 核工坊Qt  # noqa: E402

应用 = QApplication.instance() or QApplication(sys.argv)
窗 = 核工坊Qt.主窗()

基线 = len(窗.findChildren(QAction))
print("启动后 QAction 数：%d" % 基线)

# 不 exec（exec 是模态嵌套事件循环，会卡住），
# 改为把 弹主菜单 的建菜单部分单独跑出来。
# 这里直接数：连续调用 弹主菜单 会在 exec 处阻塞，
# 所以改用「用 QTimer 立刻关掉菜单」的方式。
from PySide6.QtCore import QEvent, QTimer  # noqa: E402

次数 = 15
for i in range(次数):
    # 让菜单自己弹出并在下一轮事件里关掉
    def 关():
        for m in 应用.topLevelWidgets():
            if m.__class__.__name__ == "QMenu" and m.isVisible():
                m.close()
    QTimer.singleShot(0, 关)
    try:
        窗.弹主菜单(窗.顶行.品牌字)
    except Exception as e:  # noqa: BLE001
        print("  第 %d 次开菜单异常：%r" % (i, e))
        break
    # deleteLater 排的 DeferredDelete 要靠 sendPostedEvents 才会真正执行
    应用.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    应用.processEvents()

之后 = len(窗.findChildren(QAction))
应用.processEvents()
应用.processEvents()
之后2 = len(窗.findChildren(QAction))
print("开 %d 次菜单后 QAction 数：%d（再刷两轮事件后：%d）" % (次数, 之后, 之后2))
增量 = 之后2 - 基线
print("增量：%d" % 增量)

# 看看剩下这 44 个的父对象是谁
剩 = 窗.findChildren(QAction)
if 剩:
    父们 = {}
    for a in 剩:
        p = a.parent()
        键 = p.__class__.__name__ if p else "None"
        父们[键] = 父们.get(键, 0) + 1
    print("剩下 %d 个 QAction 的父对象：%s" % (len(剩), 父们))
    菜单父 = [a for a in 剩 if a.parent() and a.parent().__class__.__name__ == "QMenu"]
    if 菜单父:
        mp = 菜单父[0].parent()
        print("  菜单的父对象：%s，可见=%s" % (
            mp.__class__.__name__ if mp else "None",
            mp.isVisible() if mp else "-"))
        print("  菜单还被引用着吗：", mp in 应用.topLevelWidgets() or (mp.parent() is not None))

if 增量 > 0:
    print()
    print("[!] 确认泄漏：每次开菜单都往主窗里堆一批 QAction，永不释放")
    print("    触发：用户反复点「☰」菜单（几十次很正常），内存持续增长")
    print("    建议：菜单用完即毁 —— 弹主菜单 结尾加 菜单.deleteLater()，")
    print("          或把 QAction 的父对象改成 菜单 而不是 self")
else:
    print("未发现 QAction 累积")

print()
print("== 菜单里的快捷键提示与勾选态 ==")
问题 = []
菜单 = 窗._建主菜单()
子 = {m.title(): m for m in 菜单.findChildren(type(菜单)) if m.title()}
编辑 = 子.get("编辑")
if 编辑 is None:
    问题.append("找不到「编辑」子菜单")
else:
    有键 = {a.text(): a.shortcut().toString() for a in 编辑.actions() if a.text()}
    for 名 in ("撤销", "重做", "剪切", "复制", "粘贴", "全选"):
        if not 有键.get(名):
            问题.append("「%s」菜单项没画快捷键" % 名)
    if 有键.get("撤销") != "Ctrl+Z":
        问题.append("撤销的键面不是 Ctrl+Z：%r" % 有键.get("撤销"))
视图 = 子.get("视图")
if 视图 is None:
    问题.append("找不到「视图」子菜单")
else:
    主题项 = [a for a in 视图.actions() if a.text().endswith("主题")]
    if len(主题项) != 2:
        问题.append("视图里的主题项不是两条：%d" % len(主题项))
    for a in 主题项:
        if not a.isCheckable():
            问题.append("「%s」不是可勾选动作" % a.text())
        应勾 = a.text() == 窗.主题名 + "主题"
        if a.isChecked() != 应勾:
            问题.append("「%s」勾选态与实际主题不符" % a.text())
菜单.deleteLater()
应用.sendPostedEvents(None, QEvent.Type.DeferredDelete)
for 说明 in 问题:
    print("  !!   %s" % 说明)
if not 问题:
    print("  ok   编辑项都画了快捷键，主题项勾选态正确")

sys.exit(1 if (增量 > 0 or 问题) else 0)
