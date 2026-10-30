# -*- coding: utf-8 -*-
"""逐项验证 Qt 版功能：菜单、快捷键、开关、对话框。"""

import os
import shutil
import sys
import tempfile
import time

# 仓库根目录 = 本脚本所在目录的上一级。
# 以前三处硬编码 r"D:" + 分隔符 + "dsh" + 分隔符 + "dsh5"：换台机器（或换个盘）
# 跑测试时 sys.path 指向不存在的目录 → import 直接失败；更坏的是「样例」
# 那处 os.path.exists 为假时会**静默跳过**整段运行测试，看着全绿实际没测。
根目录 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 根目录)
sys.argv = ["x"]

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication, QMenu

import 主题
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
    # 剪贴板得先探一下能不能用。
    #
    # 为什么必须探：有些环境里整个剪贴板就是不可用的 —— 不是「偶尔被
    # 别的程序占用」，而是彻底打不开。实测在非交互会话里 Qt 报
    #   OleSetClipboard: Failed ... COM error 0x800401d0: OpenClipboard 失败
    # 连直接 clipboard().setText("ABC") 都读不回来；同一台机上
    # PowerShell 的 Set-Clipboard 和 cmd 的 clip 也一并报「拒绝访问」。
    # 这种时候「复制可用」和「粘贴恢复」必然失败，但那不是产品缺陷 ——
    # 断言却把它记成回归失败，让人以为复制粘贴坏了。
    #
    # 这和本文件下面 [文件操作] 里的处理是同一条口径：那里早就写明
    # 「只验证调用不抛异常，不校验剪贴板内容」。同一件事两套标准，
    # 一边放过、一边判死，只会制造假红灯。
    #
    # 探法：写入一个探针串再读回来。读回来一致才认为剪贴板能用。
    # 注意不能拿「读回来为空」当不可用 —— 空也可能是剪贴板里本来就是空的，
    # 所以探针串用非空内容，且写入后立刻读。
    剪贴板可用 = False
    try:
        应用.clipboard().setText("剪贴板探针_核工坊")
        应用.processEvents()
        剪贴板可用 = 应用.clipboard().text() == "剪贴板探针_核工坊"
    except Exception:  # noqa: BLE001
        剪贴板可用 = False

    e.copy()
    应用.processEvents()
    if 剪贴板可用:
        查(bool(应用.clipboard().text()), "复制可用：%r" % 应用.clipboard().text()[:10])
    else:
        print("  --  跳过「复制可用 / 粘贴恢复」：本机剪贴板不可用（OS 拒绝访问），")
        print("      不是产品缺陷。要验这两项请在能正常复制粘贴的桌面会话里跑。")
    e.selectAll()
    应用.processEvents()
    查(e.textCursor().hasSelection(), "全选可用")
    e.cut()
    应用.processEvents()
    查(e.取文本() == "", "剪切清空了内容")
    if 剪贴板可用:
        e.paste()
        应用.processEvents()
        查("测试" in e.取文本(), "粘贴恢复")
    else:
        # 剪贴板不可用时 cut 已经把内容清空了，paste 补不回来 ——
        # 这不是编辑器的错，所以不判失败。但要把内容还原，
        # 免得后面的用例拿到空文档。
        e.置文本("测试 内容")

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
    # 剪贴板在 Windows 上可能被别的程序短暂占用（实测偶发
    # "OleSetClipboard: OpenClipboard 失败"），那是环境问题、
    # 不是产品缺陷。这里只验证「调用不抛异常」，不校验剪贴板内容。
    try:
        w._复制路径(0)
        查(True, "复制路径不报错")
    except Exception as e:  # noqa: BLE001
        查(False, "复制路径不报错（%s）" % e)

    print("[运行与停止]")
    样例 = os.path.join(根目录, "例子", "01_你好.xht")
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

    # —— 以下为 0.0.13 的修复补测 ——

    print("[替换要遵守「区分大小写」]")
    e3 = w.当前
    e3.置文本("Alpha alpha ALPHA\n")
    应用.processEvents()
    d2 = 查找对话框.查找对话框(w, e3)
    d2.查找框.setText("Alpha")
    d2.替换框.setText("甲")
    d2.勾区分.setChecked(True)
    d2.全部替换()
    应用.processEvents()
    查(e3.取文本() == "甲 alpha ALPHA\n",
       "勾了区分大小写后只换精确匹配（实际 %r）" % e3.取文本())
    e3.置文本("Alpha alpha ALPHA\n")
    d2.勾区分.setChecked(False)
    d2.全部替换()
    应用.processEvents()
    查(e3.取文本() == "甲 甲 甲\n",
       "不勾时全部替换（实际 %r）" % e3.取文本())
    # 替换当前也要守同一条规矩：不能换掉大小写不同的那个
    e3.置文本("alpha Alpha\n")
    游3 = e3.textCursor()
    游3.setPosition(0)
    e3.setTextCursor(游3)
    d2.勾区分.setChecked(True)
    d2.替换当前()
    应用.processEvents()
    查(e3.取文本() == "alpha 甲\n",
       "替换当前 也认区分大小写（实际 %r）" % e3.取文本())
    d2.close()

    print("[关闭其他标签要问要不要保存]")
    # 批量关闭以前比单个关闭还危险：先把 已改 抹成 False 再强制关，
    # 用户改了好几个文件后右键「关闭其他」，未保存的修改无声无息全丢。
    原问题框 = m.QMessageBox.question
    _问过 = []

    def _假问题框(*a, **k):
        _问过.append(a[2] if len(a) > 2 else "")
        return m.QMessageBox.Cancel     # 一律「取消」

    m.QMessageBox.question = _假问题框
    try:
        w.新建()
        w.新建()
        w.新建()
        应用.processEvents()
        底 = len(w.文档集)
        for x in w.文档集:
            x.已改 = True
        w._关闭其他标签(0)
        应用.processEvents()
        查(_问过, "关闭其他会弹保存确认（问过 %d 次）" % len(_问过))
        查(len(w.文档集) == 底, "回答「取消」时一个都不关（%d/%d）" % (len(w.文档集), 底))
    finally:
        m.QMessageBox.question = 原问题框
        for x in list(w.文档集)[1:]:
            x.已改 = False
            w.关闭文档(x, 强制=True)
        应用.processEvents()

    print("[控制台保留原换行]")
    w.清空控制台()
    w._写控制台("请输入：")
    w._写控制台("小明\n")
    w._写控制台("下一行\n")
    台 = w.控制台.toPlainText()
    查("请输入：小明" in 台, "不带换行的输出不被拆成两行（实际 %r）" % 台)
    查(台.count("\n") == 2, "换行次数与原文一致（实际 %r）" % 台)

    print("[连续运行不串台]")
    # 运行() 以前清了控制台却没清 self._输出 队列：上一进程的读线程已经读到、
    # 还没被吸走的输出会打在新一轮的开头。
    甲 = os.path.join(目录, "甲.xht")
    with open(甲, "w", encoding="utf-8") as f:
        f.write('核导入 time\n核说("甲第一段")\ntime.sleep(0.6)\n核说("甲第二段")\n')
    乙 = os.path.join(目录, "乙.xht")
    with open(乙, "w", encoding="utf-8") as f:
        f.write('核说("乙的输出")\n')
    w.打开(甲)
    应用.processEvents()
    w.运行()
    截止 = time.time() + 8
    while time.time() < 截止:
        应用.processEvents()
        time.sleep(0.02)
        if "甲第一段" in w.控制台.toPlainText():
            break
    查("甲第一段" in w.控制台.toPlainText(), "第一个程序跑起来了")
    w.打开(乙)
    应用.processEvents()
    w.运行()
    截止 = time.time() + 10
    while time.time() < 截止:
        应用.processEvents()
        time.sleep(0.02)
        if w.进程 is None:
            break
    台2 = w.控制台.toPlainText()
    查("乙的输出" in 台2, "第二个程序的输出在（实际 %r）" % 台2)
    查("甲第一段" not in 台2, "上一次运行的输出没有串进来（实际 %r）" % 台2)

    print("[运行状态点真的会变色]")
    w.竖条.设状态点("运行")
    图运行 = w.竖条.状态点.pixmap().toImage()
    w.竖条.设状态点("空闲")
    图空闲 = w.竖条.状态点.pixmap().toImage()
    # 它是自绘的 QPixmap —— 以前用 setStyleSheet("color:…") 改，
    # QSS 的 color 对 pixmap 完全没有作用，点永远是绿的。
    查(图运行 != 图空闲, "运行/空闲两张图不一样（pixmap 真的重画了）")
    查(w.竖条.状态点.pixmap().width() > 0, "状态点有图形")

    print("[换主题时已打开的对话框跟着换]")
    颜色 = 主题.取主题(w.主题名)
    另名 = [n for n in 主题.主题集 if n != w.主题名][0]
    d3 = 查找对话框.查找对话框(w, w.当前)
    d3.show()
    旧表 = d3.styleSheet()
    w.换主题(另名)
    应用.processEvents()
    查(d3.styleSheet() != 旧表, "换主题后对话框样式表被换掉")
    查(d3.styleSheet() == w.styleSheet(), "对话框样式表与主窗一致")
    w.换主题(颜色["名"])
    d3.close()
    应用.processEvents()

    print("[版本控制：重命名条目的路径]")
    sys.path.insert(0, 根目录)
    import 版本控制 as 版控

    # porcelain v1 的重命名写成 "旧名 -> 新名"。原样存下来的话，
    # 双击时会拿 目录/「旧名 -> 新名」去找文件，必然打不开。
    目录仓 = tempfile.mkdtemp(prefix="核版本重命名_")
    路径仓 = os.path.join(目录仓, "旧名.xht")
    with open(路径仓, "w", encoding="utf-8") as f:
        f.write('核说("改名前")\n')
    版控._跑(目录仓, ["init", "-q"])
    版控._跑(目录仓, ["add", "-A"])
    版控._跑(目录仓, ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"])
    os.rename(路径仓, os.path.join(目录仓, "新名.xht"))
    版控._跑(目录仓, ["add", "-A"])
    状态 = 版控.状态(目录仓)
    改动 = [p for _, p in 状态.get("改动") or []]
    查(all("->" not in p for p in 改动), "改动路径里不含「->」（%r）" % 改动)
    查(all(os.path.exists(os.path.join(目录仓, p)) for p in 改动),
       "每条改动路径都能在磁盘上找到（%r）" % 改动)
    shutil.rmtree(目录仓, ignore_errors=True)

    print("[退出清理]")
    for x in list(w.文档集):
        x.已改 = False
        w.关闭文档(x, 强制=True)
    应用.processEvents()
    查(len(w.文档集) == 0, "全部关闭")
    w.停止(静默=True)
    w.close()

    shutil.rmtree(目录, ignore_errors=True)

    print()
    if 失败:
        print("失败 %d 项：%s" % (len(失败), "；".join(失败)))
        return 1
    print("逐项验证全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(主())
