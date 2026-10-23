# -*- coding: utf-8 -*-
"""逐项验证 Qt 版功能：菜单、快捷键、开关、对话框。"""

import os
import sys
import tempfile
import time

sys.path.insert(0, r"D:\dsh\dsh5")
sys.argv = ["x"]

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication, QMenu

import 核工坊Qt as m
import 查找对话框
import 设置窗口Qt

失败 = []


def 查(条件, 说明):
    if 条件:
        print("  ok   %s" % 说明)
    else:
        print("  FAIL %s" % 说明)
        失败.append(说明)


def 主():
    应用 = QApplication([])
    w = m.主窗()
    w.show()
    应用.processEvents()
    目录 = tempfile.mkdtemp()

    print("[菜单结构]")
    查(w.顶行.菜单钮.text() == "☰", "主菜单入口存在")

    print("[编辑菜单项]")
    e = w.当前
    e.置文本("测试 内容")
    游 = e.textCursor()
    游.select(QTextCursor.Document)
    e.setTextCursor(游)
    应用.processEvents()
    e.copy()
    应用.processEvents()
    查(bool(应用.clipboard().text()), "复制可用：%r" % 应用.clipboard().text()[:10])
    e.selectAll()
    应用.processEvents()
    查(e.textCursor().hasSelection(), "全选可用")
    e.cut()
    应用.processEvents()
    查(e.取文本() == "", "剪切清空了内容")
    e.paste()
    应用.processEvents()
    查("测试" in e.取文本(), "粘贴恢复")

    print("[撤销重做]")
    e.undo()
    应用.processEvents()
    e.redo()
    应用.processEvents()
    查(True, "撤销重做不崩溃")

    print("[视图开关]")
    w.切换行号()
    应用.processEvents()
    查(not w.当前.行号.isVisible(), "行号可关")
    w.切换行号()
    应用.processEvents()
    查(w.当前.行号.isVisible(), "行号可开")
    原 = w.显示缩进线
    w.切换缩进线()
    应用.processEvents()
    查(w.显示缩进线 != 原, "缩进线可切")
    w.切换缩进线()

    print("[标签操作]")
    w.新建()
    w.新建()
    应用.processEvents()
    查(w.标签栏.count() == 3, "三个标签")
    w._关闭其他标签(0)
    应用.processEvents()
    查(w.标签栏.count() == 1, "关闭其他后剩 1 个")

    print("[查找对话框]")
    e2 = w.当前
    e2.置文本("甲\n乙\n甲\n")
    d = 查找对话框.查找对话框(w, e2)
    d.查找框.setText("甲")
    d.替换框.setText("丁")
    d.全部替换()
    应用.processEvents()
    查(e2.取文本().count("丁") == 2, "全部替换 2 处")
    d.close()

    print("[转到行]")
    j = 查找对话框.跳转对话框(w, e2)
    j.框.setText("2")
    j.跳()
    应用.processEvents()
    查(e2.当前行列()[0] == 2, "跳到第 2 行")

    print("[设置窗口四页]")
    s = 设置窗口Qt.设置对话框(w)
    for i in range(4):
        s.左栏.setCurrentRow(i)
        应用.processEvents()
        查(s.栈.currentIndex() == i, "第 %d 页可切换（%s）" % (i + 1, s.标题.text()))
    s.取消()

    print("[文件操作]")
    路径 = os.path.join(目录, "a.xht")
    e2.文件路径 = 路径
    查(w.保存(e2), "保存成功")
    查(os.path.exists(路径), "文件落盘")
    查(w.打开(路径) is e2, "重复打开复用标签")
    查(w._复制路径(0) is None, "复制路径不报错")

    print("[运行与停止]")
    样例 = os.path.join(r"D:\dsh\dsh5", "例子", "01_你好.xht")
    if os.path.exists(样例):
        w.打开(样例)
        应用.processEvents()
        w.运行()
        截止 = time.time() + 15
        while time.time() < 截止:
            应用.processEvents()
            time.sleep(0.02)
            if w.进程 is None:
                break
        查("你好世界" in w.控制台.toPlainText(), "运行有输出")
        查("返回 0" in w.控制台.toPlainText(), "结束码 0")

    print("[退出清理]")
    for x in list(w.文档集):
        x.已改 = False
        w.关闭文档(x, 强制=True)
    应用.processEvents()
    查(len(w.文档集) == 0, "全部关闭")
    w.停止(静默=True)
    w.close()

    import shutil
    shutil.rmtree(目录, ignore_errors=True)

    print()
    if 失败:
        print("失败 %d 项：%s" % (len(失败), "；".join(失败)))
        return 1
    print("逐项验证全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(主())
