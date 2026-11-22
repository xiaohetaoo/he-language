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
import 核
import 核工坊Qt as m
import 查找对话框
import 设置窗口Qt
import 版本控制窗口

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
        if "测试" in e.取文本():
            查(True, "粘贴恢复")
        else:
            # 探针到这里之间剪贴板可能被别的程序抢走 —— Windows 上实测偶发：
            #   OleSetClipboard: Failed ... COM error 0x800401d0:
            #   OpenClipboard 失败（被占用）
            # 那种情况下上面的 cut 已经把内容清空、paste 自然补不回来，
            # 不是编辑器的问题。重新探一次再定性：还能用才算真失败。
            还能用 = False
            try:
                应用.clipboard().setText("剪贴板探针_核工坊")
                应用.processEvents()
                还能用 = 应用.clipboard().text() == "剪贴板探针_核工坊"
            except Exception:  # noqa: BLE001
                还能用 = False
            if 还能用:
                查(False, "粘贴恢复")
            else:
                print("  --  跳过「粘贴恢复」：剪贴板中途被别的程序占用，")
                print("      不是产品缺陷。")
                e.置文本("测试 内容")
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

    print("[打开文件后标签选中态必须同步]")
# 回归：addTab 在 QTabBar 非空时**不会**自动选中，而 打开() 只调
# _显示文档 切内容 —— 于是打开新文件后标签高亮停在旧标签、
# 内容区已经是新文件。实测三连确认（打开甲、打开乙都停在「未命名」）。
# 快速打开 / 双击项目树 / 拖放全走这条路，所以修在 _显示文档 本身。
    import tempfile as _tf
    _d = _tf.mkdtemp(prefix="核标签同步_")
    _甲 = os.path.join(_d, "甲.xht")
    _乙 = os.path.join(_d, "乙.xht")
    for _p, _文 in ((_甲, "核说(1)" + chr(92) + "n"), (_乙, "核说(2)" + chr(92) + "n")):
        with open(_p, "w", encoding="utf-8") as _f:
            _f.write(_文)

    def _标签一致():
        _i = w.标签栏.currentIndex()
        _当 = w.标签栏.tabText(_i) if _i >= 0 else ""
        # 名字口径跟主窗走：无路径文档可能是「未命名 2」这种带序号的
        # 唯一标题（0.2.7 起），不能再硬编码成「未命名」。
        _名 = w._文件名(w.当前) if w.当前 else "未命名"
        return _名 == _当, "%s vs %s" % (_名, _当)

    w.新建()
    应用.processEvents()
    _好, _说 = _标签一致()
    查(_好, "新建后标签与内容一致（%s）" % _说)
    _e甲 = w.打开(_甲)
    应用.processEvents()
    _好, _说 = _标签一致()
    查(_好, "打开甲后标签跟到甲（%s）" % _说)
    _e乙 = w.打开(_乙)
    应用.processEvents()
    _好, _说 = _标签一致()
    查(_好, "打开乙后标签跟到乙（%s）" % _说)
# 反向也要对：把当前切回甲，标签得跟回去
    w._显示文档(_e甲)
    应用.processEvents()
    _好, _说 = _标签一致()
    查(_好, "切回甲后标签跟回甲（%s）" % _说)
    # 收尾：把文档数清回 1 个，否则下面「三个标签」那条按绝对数量断言就会失败。
    # （这是我加用例时踩的：本来以为只是「多开了几个标签」，但下一条
    #   断言的是 count()==3 这个**绝对值**，残留几个都会错。）
    w.新建()
    应用.processEvents()
    while w.标签栏.count() > 1:
        w._关闭其他标签(0)
        应用.processEvents()
    查(w.标签栏.count() == 1, "新用例收尾后回到 1 个标签")

    print("[关机存盘后必须复位 _正在退出]")
# 回归：_会话要关机 置 _正在退出=True 且从不复位。系统发了
# commitDataRequest 之后用户**可能取消关机**（Windows 会问
# 「还有程序没关，要强制关机吗」）。一旦取消，程序继续用，
# 但标志留着 True → 之后再关窗 closeEvent 直接 accept，
# 关机存盘之后的新改动被静默丢弃（实测：残留 True、弹框 0 次）。
    _关机后 = w._正在退出
    w._会话要关机()
    应用.processEvents()
    查(w._正在退出 is False, "关机存盘后 _正在退出 已复位（调后=%r）" % w._正在退出)

    print("[关机不许永久停后台、未命名文档要留恢复文件]")
    # P1-15：会话管理器发 commitDataRequest 时**不一定是真关机** ——
    # 用户可以在系统弹的确认里选「取消」。所以这里只能做「尽快保存」，
    # 绝不能把 运行进程 / 版本查询器 永久停掉，也不能把没保存的未命名
    # 文档直接跳过。
    _保存前进程 = getattr(w, "_进程", None)
    w.新建()
    w.当前.置文本("甲 = 1\n乙 = 2\n", 标记已改=True)
    _恢复目录 = os.path.join(tempfile.gettempdir(), "核工坊-恢复")
    _之前恢复 = set(os.listdir(_恢复目录)) if os.path.isdir(_恢复目录) else set()
    w._会话要关机()
    应用.processEvents()
    _之后恢复 = set(os.listdir(_恢复目录)) if os.path.isdir(_恢复目录) else set()
    新恢复 = _之后恢复 - _之前恢复
    查(bool(新恢复), "未命名文档写出了恢复文件（新增 %d 个）" % len(新恢复))
    if 新恢复:
        _内容 = ""
        try:
            with open(os.path.join(_恢复目录, sorted(新恢复)[0]), encoding="utf-8") as f:
                _内容 = f.read()
        except OSError:
            pass
        查("甲 = 1" in _内容, "恢复文件里是文档内容")
        查(_内容 == w.当前.取文本(), "恢复文件内容与编辑器一致")
    # 后台不能被永久停掉
    _查询器 = getattr(w, "_版本查询", None)
    查(_查询器 is None or not getattr(_查询器, "_停", False),
       "关机保存后版本查询器没有被永久停掉")
    # 这一段自建的文档要收干净，否则后面 [标签操作] 的计数就对不上
    for _d in list(w.文档集):
        if _d.文件路径 is None and _d.未命名标题 not in ("未命名",):
            _d.已改 = False
            w.关闭文档(_d, 强制=True)
    应用.processEvents()

    print("[串内冒号行不是块开头]")
    # P1-11：三引号串里的一行「注意：」如果被当成块开头，回车会多缩一级、
    # 折叠也会在字符串内部折起来。
    _编 = w.新建()
    _编.置文本('甲 = """\n注意：\n    内容\n"""\n')
    _块 = _编.document().findBlockByNumber(1)
    查(_编.可折叠(_块) is False, "三引号串里的「注意：」不可折叠")
    查(_编.是块开头(_块.text(), _编._起始串(_块)) is False,
       "三引号串里的「注意：」不是块开头")
    查(_编.是块开头("注意：", None) is True, "串外同样的文本仍是块开头")
    _编.已改 = False
    w.关闭文档(_编, 强制=True)

    print("[嵌套折叠要递归展开]")
    # P1-16：先折内层再折外层，光标落在内层隐藏行时只展开外层是不够的。
    _编 = w.新建()
    _编.置文本("核若 核对：\n    核若 核对：\n        核说(1)\n    核说(2)\n核说(3)\n")
    _外层 = _编.document().findBlockByNumber(0)
    _内层 = _编.document().findBlockByNumber(1)
    _编._数据(_内层, 需要时新建=True).折叠 = True
    _编.应用折叠()
    _编._数据(_外层, 需要时新建=True).折叠 = True
    _编.应用折叠()
    应用.processEvents()
    _编.setTextCursor(QTextCursor(_编.document().findBlockByNumber(2)))
    _编._展开含此块的折叠(2)
    应用.processEvents()
    _表 = getattr(_编, "_可见表", None)
    查(bool(_表) and _表[2], "展开后第 3 行可见（两层都展开了）")
    查(bool(_表) and _表[_编.textCursor().blockNumber()], "光标落在可见行上")
    _编.已改 = False
    w.关闭文档(_编, 强制=True)

    print("[状态栏长文本必须省略且不挤掉右侧]")
    # P2-21
    _长 = "配置文件有 3 处不合法，已回退默认：制表宽、项目目录、窗口尺寸" * 3
    w.状态(_长)
    应用.processEvents()
    查(w.状态左.text() != _长 and "…" in w.状态左.text(), "长状态文本被省略")
    查(w.状态左.toolTip() == _长, "全文进了 tooltip")
    查(w.状态右.width() >= 200, "右侧信息没被挤掉（宽 %d）" % w.状态右.width())
    w.状态("已保存")

    print("[分割条命中宽度]")
    # P2-20：1px 的 handle 实际上拖不动
    查(w.横栏.handleWidth() >= 4, "水平分割条 ≥4px（实际 %d）" % w.横栏.handleWidth())
    查(w.分栏.handleWidth() >= 4, "垂直分割条 ≥4px（实际 %d）" % w.分栏.handleWidth())

    print("[最近打开：失效路径必须自动摘掉]")
    # P2-27：配置里那份 self.最近 是跨会话累积的。临时文件被删、U 盘拔掉、
    # 项目改名之后，条目就变成死链接 —— 点开只弹「文件不存在」。
    # 以前菜单照列不误，用户只能自己去翻配置文件。
    _活1 = os.path.join(目录, "还在1.xht")
    _活2 = os.path.join(目录, "还在2.xht")
    for _p in (_活1, _活2):
        with open(_p, "w", encoding="utf-8") as _f:
            _f.write("核说(1)\n")
    _死 = [os.path.join(目录, "早删了%d.xht" % i) for i in range(3)]
    w.最近 = [_死[0], _活1, _死[1], _活2, _死[2]]
    _菜单 = w._建主菜单()
    _文件菜单 = None
    for _a in _菜单.actions():
        if _a.text() == "文件":
            _文件菜单 = _a.menu()
            break
    查(_文件菜单 is not None, "主菜单里找得到「文件」")
    _最近菜单 = None
    if _文件菜单 is not None:
        for _a in _文件菜单.actions():
            if _a.text() == "最近打开":
                _最近菜单 = _a.menu()
                break
    查(_最近菜单 is not None, "文件菜单里找得到「最近打开」")
    _条目 = [a.text() for a in _最近菜单.actions()] if _最近菜单 else []
    _路径项 = [t for t in _条目 if t not in ("", "（空）")
               and not t.startswith("清理失效项")]
    查(len(_路径项) == 2, "只列出仍然存在的 2 个文件（实际 %r）" % (_路径项,))
    # 菜单项文字是**文件名**（不是全路径），所以按 basename 对回真实存在的文件
    _应显示 = {os.path.basename(p) for p in (_活1, _活2)}
    查(set(_路径项) == _应显示,
       "列出的是那两个活着的文件（期望 %r）" % (sorted(_应显示),))
    _清理 = [a for a in (_最近菜单.actions() if _最近菜单 else [])
             if a.text().startswith("清理失效项")]
    查(len(_清理) == 1, "底部有「清理失效项」入口")
    查(bool(_清理) and "3" in _清理[0].text(),
       "清理入口写明条数 3（实际 %r）" % (_清理[0].text() if _清理 else ""))
    查(len(w.最近) == 2, "内存里的 最近 也已摘掉失效项（剩 %d）" % len(w.最近))
    for _p in (_活1, _活2):
        try:
            os.remove(_p)
        except OSError:
            pass

    print("[对照表等号必须按显示宽度对齐]")
    # P2-25：中文占两列，用 %-*s 按字符补空格会让等号歪掉
    _线 = [l for l in w.对照.toPlainText().split("\n") if " = " in l][:40]
    _列 = {m.主窗._显示宽度(l.split(" = ")[0]) for l in _线}
    查(len(_列) <= 3, "等号列宽收敛（%r）" % sorted(_列))

    print("[复选框三态真的画了勾]")
    # P2-24：QSS 的 ::indicator 画不出对勾，改用自绘。
    from PySide6.QtWidgets import QCheckBox  # noqa: E402

    _样 = getattr(应用, "_核控件样式", None)
    查(_样 is not None, "已装上自绘控件样式")
    _勾 = QCheckBox("x")
    _勾.resize(120, 24)
    _勾.show()
    应用.processEvents()
    _图1 = _勾.grab().toImage()
    _勾.setChecked(True)
    应用.processEvents()
    _图2 = _勾.grab().toImage()
    _不同 = sum(
        1
        for x in range(min(_图1.width(), _图2.width()))
        for y in range(min(_图1.height(), _图2.height()))
        if _图1.pixelColor(x, y) != _图2.pixelColor(x, y)
    )
    查(_不同 > 30, "选中/未选中画面明显不同（%d 像素）" % _不同)
    # 勾线颜色必须和底色不同，即真有「勾」而不只是一块纯色
    _强调 = 主题.取主题(w.主题名)["强调"].lower()
    _白 = 0
    for x in range(2, 16):
        for y in range(2, 16):
            c = _图2.pixelColor(x, y)
            if c.red() > 200 and c.green() > 200 and c.blue() > 200:
                _白 += 1
    查(_白 > 3, "选中态里有浅色勾线（%d 个像素）" % _白)
    _勾.deleteLater()


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

    print("[文件去重：同一文件的不同写法只开一个标签]")
    # P1-4：以前只比较路径字符串，`a.xht` / `./a.xht` / `A.XHT` 会被当成
    # 三个不同文件各开一个标签，改一个存盘就把另外两个的改动盖掉。
    _去重路径 = os.path.join(目录, "去重.xht")
    with open(_去重路径, "w", encoding="utf-8") as _f:
        _f.write("核说(1)\n")
    _甲 = w.打开(_去重路径)
    _数前 = len(w.文档集)
    _同1 = w.打开(os.path.join(目录, ".", "去重.xht"))
    _同2 = w.打开(os.path.join(目录, "去重.XHT"))
    查(_同1 is _甲, "带 ./ 的写法复用同一个编辑器")
    查(_同2 is _甲, "大小写不同的写法复用同一个编辑器")
    查(len(w.文档集) == _数前, "没有多开标签（%d → %d）" % (_数前, len(w.文档集)))

    print("[外部修改后保存必须先问一句]")
    # P1-5：磁盘上的文件被别人改过，Ctrl+S 直接覆盖会把人家的改动抹掉。
    _外部路径 = os.path.join(目录, "外部.xht")
    with open(_外部路径, "w", encoding="utf-8") as _f:
        _f.write("核说(1)\n")
    _乙 = w.打开(_外部路径)
    _乙.置文本("核说(2)\n", 标记已改=True)
    time.sleep(0.02)
    with open(_外部路径, "w", encoding="utf-8") as _f:
        _f.write("核说(9)\n")
    _原问 = m.主窗._问覆盖外部修改
    _答复 = {"值": "cancel"}
    m.主窗._问覆盖外部修改 = lambda self, 编: _答复["值"]
    try:
        查(w.保存(_乙) is False, "选「取消」时保存返回 False")
        with open(_外部路径, encoding="utf-8") as _f:
            查(_f.read() == "核说(9)\n", "磁盘上的外部改动没被覆盖")
        _答复["值"] = "overwrite"
        查(w.保存(_乙) is True, "选「覆盖」时保存成功")
        with open(_外部路径, encoding="utf-8") as _f:
            查(_f.read() == "核说(2)\n", "磁盘被写成编辑器里的内容")
    finally:
        m.主窗._问覆盖外部修改 = _原问

    print("[重命名要挡住非法文件名]")
    # P1-9：返回的是 (清洗后的名字, 原因) 二元组
    for _坏 in ("../跑出去", "a/b", "a\\b", "..", "", "x:y", "a?b", "a*b"):
        _得 = m.主窗._合法文件名(_坏)
        查(_得[0] is None, "拒绝非法名 %r（原因：%s）" % (_坏, _得[1]))
    查(m.主窗._合法文件名("正常名")[0] == "正常名.xht", "没写扩展名时自动补 .xht")
    查(m.主窗._合法文件名("带空格 的名字.xht")[0] == "带空格 的名字.xht",
       "合法名字原样通过")
    查(m.主窗._合法文件名("别的.PY")[0] == "别的.PY.xht",
       "非 .xht 结尾时补上 .xht（否则项目树认不出来）")

    print("[在项目中查找：非 UTF-8 文件要跳过而不是崩]")
    # P1-13：以前固定 errors="replace"，坏文件读出来是乱码、搜不到还以为是
    # 自己记错了；正确做法是把读不了的**明确列出来**。
    with open(os.path.join(目录, "坏编码.xht"), "wb") as _f:
        _f.write(b"\xff\xfe\x00\x01\xff\x80 not utf8 and not gbk")
    with open(os.path.join(目录, "好文件.xht"), "w", encoding="utf-8") as _f:
        _f.write("苹果 = 1\n")
    _原目录 = w.项目目录
    w.装载项目树(目录, 记住=False)
    from PySide6.QtWidgets import QInputDialog

    _原输入 = QInputDialog.getText
    QInputDialog.getText = staticmethod(lambda *a, **k: ("苹果", True))
    try:
        w.在项目中查找()
    finally:
        QInputDialog.getText = _原输入
        w.装载项目树(_原目录, 记住=False)
    _台 = w.控制台.toPlainText()
    查("好文件.xht" in _台, "正常文件被搜到")
    查("跳过" in _台, "报告了被跳过的文件（不静默忽略）")
    查("坏编码.xht" in _台, "跳过的文件名写清楚了")

    print("[临时浏览别的目录不许写进配置]")
    # P1-14：打开单个文件时项目树会临时指向它的目录；以前这会把
    # 「项目目录」永久改掉，下次启动项目树就是错的。
    _原持久 = w._持久项目目录
    w.装载项目树(目录, 记住=False)
    查(w.项目目录 == 目录, "树临时指向新目录")
    查(w._持久项目目录 == _原持久, "持久项目目录没被临时浏览改掉")
    w.装载项目树(_原持久, 记住=True)
    查(w._持久项目目录 == _原持久, "真正切换项目目录时才更新")

    print("[设置预览期间不许写盘]")
    # P1-6：拖字号/换主题会立刻反写到 工坊配置.json，用户按 Esc 取消后
    # 配置还是改过的值 —— 下次启动才发现字号被改了。
    import 配置

    _配置路径 = 配置.配置路径()
    with open(_配置路径, encoding="utf-8") as _f:
        _配置原文 = _f.read()
    _字号原 = w.字号
    _框 = 设置窗口Qt.设置对话框(w)
    _框.字号条.setValue(max(8, _字号原 - 2))
    应用.processEvents()
    with open(_配置路径, encoding="utf-8") as _f:
        _预览中原文 = _f.read()
    查(_预览中原文 == _配置原文, "预览期间配置文件没被改写")
    查(getattr(w, "_设置预览中", False) is True, "对话框打开时处于预览态")
    _框.取消()
    应用.processEvents()
    查(getattr(w, "_设置预览中", False) is False, "取消后预览态清掉")
    查(w.字号 == _字号原, "取消后字号回到原值（%d）" % w.字号)
    with open(_配置路径, encoding="utf-8") as _f:
        查(_f.read() == _配置原文, "取消后配置文件仍是原样")

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

        # —— 退出瞬间的输出不能丢（0.2.3 修）——
        # _读输出 以前在进程**运行中**也累计空读次数：子进程启动慢一点
        # （机器负载高时半秒以上）就攒出几十次；等它刚退出、最后一包还在
        # 管道里没被取走的那一瞬，read1 仍返回空，"已结束 and 空读 >= 3"
        # 当场成立直接 break —— 那包输出永远丢了。
        # 实测表现：控制台里有「[程序结束，返回 0]」，却看不到程序打印的
        # 内容（打包前的回归里真的撞到过一次）。
        # 修法：空读只在进程结束后才计，且 _检查进程 收尾前再主动捞一次管道。
        #
        # 诚实说明：下面这条**不能稳定复现原 bug** —— 试过把修复回退、
        # 连跑三次仍然全绿。原 bug 依赖「启动慢 + 刚好在退出瞬间读取」的
        # 时序窗口，在 offscreen 测试里很难稳定制造。它作为**端到端冒烟**
        # 仍然有价值（确认退出前的输出确实出现在控制台），但别把它当成
        # 这个 bug 的守门测试。
        import tempfile as _tf

        _d = _tf.mkdtemp(prefix="核退出输出_")
        _f = os.path.join(_d, "尾包.xht")
        with open(_f, "w", encoding="utf-8") as _h:
            _h.write(
                "核从 核时间库 核导入 核睡眠" + chr(10)
                + "核睡眠(0.6)" + chr(10)
                + '核说("退出前最后一行")' + chr(10)
            )
        w.打开(_f)
        应用.processEvents()
        w.运行()
        截止2 = time.time() + 15
        while time.time() < 截止2:
            应用.processEvents()
            time.sleep(0.02)
            if w.进程 is None:
                break
        # 再多转两圈事件循环，确保 _再捞管道 已把尾巴交出去
        for _ in range(20):
            应用.processEvents()
            time.sleep(0.02)
        _台 = w.控制台.toPlainText()
        查("退出前最后一行" in _台, "退出前的输出出现在控制台（冒烟）")
        查("返回 0" in _台, "尾包用例结束码 0")

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
    #
    # 打桩点从 QMessageBox.question 改成了 核工坊Qt._问保存三选：
    # 0.2.8 起「关闭文档」和「关窗口」两条路共用这一个三选 helper
    #（P0-1 的修法 —— 原来两处各自比 QMessageBox.Cancel，都漏掉了
    #  X/Esc 返回的 NoButton）。继续打桩 question 会打空，真弹模态框，
    # 这个用例就会永远卡住。
    原三选 = m._问保存三选
    _问过 = []

    def _假三选(父, 标题, 文本, 默认=None):
        _问过.append(文本)
        return "cancel"     # 一律「取消」

    m._问保存三选 = _假三选
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
        m._问保存三选 = 原三选
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

    print("[设置「应用」之后 Esc 不许撤销已提交的值]")
    # P1-3：字号 12 → 拖到 30 → 点应用（已生效、已写盘）→ Esc
    # 以前取消() 永远还原到「打开设置时」的基线，于是刚应用的值被无声撤销。
    _开时 = w.字号
    _框A = 设置窗口Qt.设置对话框(w)
    _框A.字号条.setValue(_开时 + 6)
    应用.processEvents()
    _框A._落实字号()
    _框A.应用()
    应用.processEvents()
    _应用值 = w.字号
    查(_应用值 == _开时 + 6, "应用后字号生效（%d）" % _应用值)
    _框A.取消()
    应用.processEvents()
    查(w.字号 == _应用值, "Esc 之后仍是已应用的字号（%d）" % w.字号)

    print("[外部删除后保存不许静默重建]")
    # P1-4：文件被外部删掉 → Ctrl+S 以前直接在原路径重建，一声不响。
    _外目录 = tempfile.mkdtemp(prefix="外部删除_", dir=目录)
    _外路径 = os.path.join(_外目录, "删了.xht")
    with open(_外路径, "w", encoding="utf-8", newline="\n") as _f:
        _f.write("甲 = 1\n")
    _编外 = w.打开(_外路径)
    _编外.置文本("甲 = 2\n", 标记已改=True)
    os.remove(_外路径)
    _原消失 = m.主窗._问文件已消失
    _答外 = {"值": "cancel"}
    m.主窗._问文件已消失 = lambda self, 编: _答外["值"]
    try:
        查(w.保存(_编外) is False, "选「取消」时保存返回 False")
        查(not os.path.exists(_外路径), "取消后磁盘上没有被重建")
        _答外["值"] = "recreate"
        查(w.保存(_编外) is True, "选「重新创建」时保存成功")
        查(os.path.exists(_外路径), "重新创建后文件回到原路径")
    finally:
        m.主窗._问文件已消失 = _原消失
    _编外.已改 = False
    w.关闭文档(_编外, 强制=True)

    print("[外部修改后重新打开要提示并重载]")
    # P2-1：磁盘内容变了，再双击同一文件以前直接返回旧编辑器（内容不刷新）。
    _重路径 = os.path.join(_外目录, "重开.xht")
    with open(_重路径, "w", encoding="utf-8", newline="\n") as _f:
        _f.write("甲 = 1\n")
    _编重 = w.打开(_重路径)
    time.sleep(0.02)
    with open(_重路径, "w", encoding="utf-8", newline="\n") as _f:
        _f.write("甲 = 9\n")
    _原磁盘 = m.主窗._问磁盘已变
    _答盘 = {"值": "reload"}
    m.主窗._问磁盘已变 = lambda self, 编: _答盘["值"]
    try:
        _答盘["值"] = "keep"
        同 = w.打开(_重路径)
        查(同 is _编重, "仍是同一个编辑器")
        查(_编重.取文本() == "甲 = 1\n", "选「保留当前」时不重载")
        _答盘["值"] = "reload"
        w.打开(_重路径)
        查(_编重.取文本() == "甲 = 9\n", "选「重新加载」后内容与磁盘一致")
        查(_编重.已改 is False, "重新加载后不算已改")
    finally:
        m.主窗._问磁盘已变 = _原磁盘
    _编重.已改 = False
    w.关闭文档(_编重, 强制=True)
    shutil.rmtree(_外目录, ignore_errors=True)

    print("[输出视图字号固定，只有编辑区正文跟随]")
    # P1-5：diffView 以前没写 font-size，继承编辑器的 __字号__px，
    # 40 号时占位文字变成巨型字；控制台/版本历史此前已固定。
    _字号记录 = {}
    for _号 in (12, 40):
        w.设字号(_号)
        应用.processEvents()
        _面板 = 版本控制窗口.版本控制窗口(w, 根目录)
        _面板.resize(560, 640)
        _面板.show()
        应用.processEvents()
        _字号记录[_号] = dict(
            差异=_面板.差异.fontMetrics().height(),
            控制台=w.控制台.fontMetrics().height(),
            编辑=w.当前.fontMetrics().height() if w.当前 else 0,
        )
        _面板.close()
        应用.processEvents()
    _差12, _差40 = _字号记录[12]["差异"], _字号记录[40]["差异"]
    查(_差12 == _差40, "diffView 字号不随编辑器变（%d / %d）" % (_差12, _差40))
    查(12 <= _差12 <= 18, "diffView 是固定小字号（%d px）" % _差12)
    _控12, _控40 = _字号记录[12]["控制台"], _字号记录[40]["控制台"]
    查(_控12 == _控40, "控制台字号不随编辑器变（%d / %d）" % (_控12, _控40))
    查(_字号记录[40]["编辑"] > _字号记录[12]["编辑"] * 2,
       "编辑区正文确实会变大（%d → %d）"
       % (_字号记录[12]["编辑"], _字号记录[40]["编辑"]))
    w.设字号(12)
    应用.processEvents()

    print("[复选框指示器固定 14px（不假装随字号缩放）]")
    # P2-2：上一版声称 13→24 缩放，实际读的是 QCheckBox 自己的字体，
    # 12 与 40 号下都是 13px，两张证据截图逐像素相同。现在是明确固定值。
    from PySide6.QtWidgets import QCheckBox, QStyle  # noqa: E402

    _尺寸 = []
    for _号 in (12, 40):
        w.设字号(_号)
        应用.processEvents()
        _勾 = QCheckBox("x")
        _勾.show()
        应用.processEvents()
        _尺寸.append((_勾.sizeHint().height(),
                      _勾.style().pixelMetric(QStyle.PM_IndicatorHeight, None, _勾)))
        _勾.close()
        _勾.deleteLater()
    查(_尺寸[0] == _尺寸[1], "两档齐高同宽（%r / %r）" % (_尺寸[0], _尺寸[1]))
    查(_尺寸[0][1] == 14, "指示器固定 14px（实际 %d）" % _尺寸[0][1])
    w.设字号(12)
    应用.processEvents()

    print("[关于页不许出现两行相同版本]")
    # P3-1：界面版本与内核版本同源于 核.版本，永远一样。
    import 帮助窗口  # noqa: E402
    from PySide6.QtWidgets import QLabel  # noqa: E402

    _关于 = 帮助窗口.关于对话框(w, 核.版本)
    _关于.show()
    应用.processEvents()
    _合并 = "\n".join(l.text() for l in _关于.findChildren(QLabel))
    查(_合并.count("v" + 核.版本) <= 1,
       "关于页最多出现一次 v%s（实际 %d）"
       % (核.版本, _合并.count("v" + 核.版本)))
    _关于.close()

    print("[重命名要挡住 Windows 保留名与尾随点空格]")
    # P3-2
    for _坏 in ("CON", "CON.xht", "NUL.xht", "COM1.xht", "LPT9", "PRN.xht",
                "AUX", "a.", "a.xht.", "带空格 "):
        查(m.主窗._合法文件名(_坏)[0] is None, "拒绝 %r" % _坏)
    for _好, _期望 in (("..foo", "..foo.xht"), ("COM10.xht", "COM10.xht"),
                       ("console.xht", "console.xht"), ("a..b", "a..b.xht")):
        查(m.主窗._合法文件名(_好)[0] == _期望, "接受 %r → %r" % (_好, _期望))

    print("[取消关窗要恢复最大化/全屏状态]")
    # P3-3：拉回来() 以前固定 showNormal()，最大化/全屏都被降级成普通窗口。
    from PySide6.QtCore import QEvent  # noqa: E402

    for _状态 in ("maximized", "fullscreen"):
        w.showNormal()
        应用.processEvents()
        if _状态 == "maximized":
            w.showMaximized()
        else:
            w.showFullScreen()
        应用.processEvents()
        _编窗 = w.新建()
        _编窗.置文本("甲 = 1\n", 标记已改=True)
        w.closeEvent(QEvent(QEvent.Close))
        应用.processEvents()
        查(getattr(w, "_关窗窗口状态", None) == _状态,
           "closeEvent 拍下了 %s 状态" % _状态)
        _编窗.已改 = False
        w._关窗待问 = []
        w._关窗确认中 = False
        w._正在退出 = False
        应用.processEvents()
        w.关闭文档(_编窗, 强制=True)
        w.showNormal()
        应用.processEvents()

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
