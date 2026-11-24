# -*- coding: utf-8 -*-
"""代码折叠验证。

要点：
  · 折叠区判定要对（冒号开头 + 下一行缩进更深）；
  · 折起来后隐藏行不占高度、行号跟着跳；
  · 展开后必须完全恢复；
  · 编辑后不能把别处的折叠弄错位（userState 跟着块走）；
  · 光标绝不能停在看不见的行上。

用法：python 测试/查折叠.py
"""

import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("核工坊_配置目录", tempfile.mkdtemp(prefix="核工坊折叠_"))

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication  # noqa: E402
from PySide6.QtGui import QTextCursor  # noqa: E402

import 核工坊Qt  # noqa: E402

应用 = QApplication.instance() or QApplication(sys.argv)
窗 = 核工坊Qt.主窗()

问题 = []


def 检(说明, 条件, 详情=""):
    if 条件:
        print("  OK  %s" % 说明)
    else:
        问题.append((说明, 详情))
        print("  !! %s" % 说明)
        if 详情:
            print("        %s" % 详情)


def 新编(文本):
    编 = 窗.新建()
    编.置文本(文本)
    return 编


样本 = """核定义 外()：
    x = 1
    核若 x：
        核说(x)
        y = 2
    核说(0)
核说(1)
"""

编 = 新编(样本)
d = 编.document()
print("== 一、折叠区判定 ==")
检("行0（核定义…：）可折叠", 编.可折叠(d.findBlockByNumber(0)))
区 = 编.折叠区(d.findBlockByNumber(0))
# 行1..行5 缩进都比行0 深（行5 是 4 空格 > 0），所以整块折到行5
检("行0 折叠到行5", 区 == 5, "实际 %r" % 区)
检("行1（x = 1）不可折叠", not 编.可折叠(d.findBlockByNumber(1)))
检("行2（核若 x：）可折叠", 编.可折叠(d.findBlockByNumber(2)))
区2 = 编.折叠区(d.findBlockByNumber(2))
检("行2 折叠到行4", 区2 == 4, "实际 %r" % 区2)
检("行5（核说(0)）不可折叠", not 编.可折叠(d.findBlockByNumber(5)))
检("行6（核说(1)）不可折叠", not 编.可折叠(d.findBlockByNumber(6)))

print("== 二、折叠后隐藏行不占高度 ==")
def 可见数():
    b = d.firstBlock()
    n = 0
    while b.isValid():
        if b.isVisible():
            n += 1
        b = b.next()
    return n

总数 = d.blockCount()
检("折叠前全部可见", 可见数() == 总数, "%d/%d" % (可见数(), 总数))
编.切换折叠(d.findBlockByNumber(0))
检("折叠后可见数变少", 可见数() < 总数, "%d/%d" % (可见数(), 总数))
检("行1-4 被隐藏", all(not d.findBlockByNumber(i).isVisible() for i in (1, 2, 3, 4)))

print("== 三、展开后完全恢复 ==")
编.切换折叠(d.findBlockByNumber(0))
检("展开后全部可见", 可见数() == 总数, "%d/%d" % (可见数(), 总数))
检("标记已清", not 编.已折叠(d.findBlockByNumber(0)))

print("== 四、全部折叠 / 全部展开 ==")
编.全部折叠()
检("全部折叠后有隐藏行", 可见数() < 总数, "%d/%d" % (可见数(), 总数))
编.全部展开()
检("全部展开后全部可见", 可见数() == 总数, "%d/%d" % (可见数(), 总数))

print("== 五、编辑后折叠不错位 ==")
编2 = 新编("核定义 a()：\n    核说(1)\n核定义 b()：\n    核说(2)\n核说(3)\n")
d2 = 编2.document()
编2.切换折叠(d2.findBlockByNumber(2))   # 折起 b
检("b 已折叠", 编2.已折叠(d2.findBlockByNumber(2)))
# 在最上面插两行，b 应该下移但仍折叠
游 = QTextCursor(d2.findBlockByNumber(0))
游.movePosition(QTextCursor.StartOfBlock)
编2.setTextCursor(游)
游.insertText("核核 新注释\n核核 又一行\n")
应用.processEvents()
# 找出新的 b 所在行
b行 = None
b = d2.firstBlock()
while b.isValid():
    if "核定义 b" in b.text():
        b行 = b.blockNumber()
        break
    b = b.next()
检("b 下移了但仍在", b行 is not None, "行号 %r" % b行)
if b行 is not None:
    检("b 仍然折叠（折叠标记跟着块走）", 编2.已折叠(d2.findBlockByNumber(b行)),
       "行%d 已折叠=%s" % (b行, 编2.已折叠(d2.findBlockByNumber(b行))))
    检("b 的下一行被隐藏", not d2.findBlockByNumber(b行 + 1).isVisible())

print("== 五之二、重新高亮不能把折叠冲掉 ==")
# 这是最初用 userState 存折叠时踩的坑：QSyntaxHighlighter 会把上一块的
# userState 往下传播，一跑高亮折叠标记就没了。改用 QTextBlockUserData 才对。
编7 = 新编("核定义 a()：\n    核说(1)\n核说(2)\n")
d7 = 编7.document()
编7.切换折叠(d7.findBlockByNumber(0))
检("折叠成功", 编7.已折叠(d7.findBlockByNumber(0)))
编7.高亮.rehighlight()
应用.processEvents()
检("rehighlight 后仍折叠", 编7.已折叠(d7.findBlockByNumber(0)),
   "userData=%r" % (d7.findBlockByNumber(0).userData(),))
检("rehighlight 后行1 仍隐藏", not d7.findBlockByNumber(1).isVisible())
# 整篇重设文本（换主题会走 换主题→重建→rehighlight）也要保住
编7.高亮.重建()
编7.高亮.rehighlight()
应用.processEvents()
检("重建规则后仍折叠", 编7.已折叠(d7.findBlockByNumber(0)))
# 关掉自动高亮也会 rehighlight
编7.设自动高亮(False)
应用.processEvents()
检("关掉高亮后仍折叠", 编7.已折叠(d7.findBlockByNumber(0)))
编7.设自动高亮(True)

print("== 六、光标不会停在隐藏行上 ==")
编3 = 新编(样本)
d3 = 编3.document()
编3.切换折叠(d3.findBlockByNumber(0))
# 强行把光标放到被隐藏的行 3
游3 = QTextCursor(d3.findBlockByNumber(3))
编3.setTextCursor(游3)
应用.processEvents()
检("光标所在行可见了（自动展开）", d3.findBlockByNumber(3).isVisible(),
   "行3 可见=%s" % d3.findBlockByNumber(3).isVisible())

print("== 七、删掉冒号后折叠标记要失效 ==")
编4 = 新编("核定义 a()：\n    核说(1)\n核说(2)\n")
d4 = 编4.document()
编4.切换折叠(d4.findBlockByNumber(0))
检("已折叠", 编4.已折叠(d4.findBlockByNumber(0)))
# 把冒号删掉
游4 = QTextCursor(d4.findBlockByNumber(0))
游4.movePosition(QTextCursor.EndOfBlock)
游4.deletePreviousChar()
应用.processEvents()
检("冒号没了 → 不再是折叠块", not 编4.已折叠(d4.findBlockByNumber(0)),
   "userState=%s" % d4.findBlockByNumber(0).userState())
检("行1 恢复可见", d4.findBlockByNumber(1).isVisible())

print("== 八、空行/缩进边界 ==")
编5 = 新编("核若 核对：\n    核说(1)\n\n    核说(2)\n核说(3)\n")
d5 = 编5.document()
区5 = 编5.折叠区(d5.findBlockByNumber(0))
检("含空行的块折叠到行3", 区5 == 3, "实际 %r" % 区5)
检("行4（同级）不在折叠区", 区5 is not None and 区5 < 4)

编6 = 新编("核若 核对：\n核说(1)\n")
d6 = 编6.document()
检("下一行没有更深缩进 → 不可折叠", not 编6.可折叠(d6.findBlockByNumber(0)))

print("== 九、全角/半角冒号都认 ==")
检("全角：", 核工坊Qt.编辑器.是块开头("核若 x："))
检("半角:", 核工坊Qt.编辑器.是块开头("核若 x:"))
检("行尾注释不影响", 核工坊Qt.编辑器.是块开头("核若 x： 核核 说明"))
检("普通语句不是块开头", not 核工坊Qt.编辑器.是块开头("核说(1)"))

print("== 十、回车自动缩进与折叠用同一套「块开头」判定 ==")
# 以前 _自动缩进 自己写 rstrip().endswith(":")，不剥行尾注释，
# 于是「核若 对： 核核 说明」后回车不缩进，而同一行却能折叠 ——
# 同一个概念两处口径不一致，用户看到的是莫名其妙的行为。
from PySide6.QtCore import QEvent, Qt  # noqa: E402
from PySide6.QtGui import QKeyEvent  # noqa: E402


def 回车后(行文):
    编9 = 新编(行文)
    游9 = 编9.textCursor()
    游9.movePosition(QTextCursor.EndOfBlock)
    编9.setTextCursor(游9)
    编9.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier, "\n"))
    return 编9.取文本().split("\n")[1]


检("带行尾注释的冒号行也缩进一级",
   回车后("核若 对： 核核 说明") == "    ",
   "第二行=%r" % 回车后("核若 对： 核核 说明"))
检("不带注释的照旧缩进", 回车后("核若 对：") == "    ")
检("非块开头只继承缩进",
   回车后("    核说(1)") == "    ",
   "第二行=%r" % 回车后("    核说(1)"))
检("缩进 + 块开头叠加",
   回车后("    核若 对： 核核 x") == "        ",
   "第二行=%r" % 回车后("    核若 对： 核核 x"))

print("== 十一、跨行括号也能折（以前只认冒号块）==")
# 真实代码里 x = [...]、d = {...}、跨行函数调用都很常见，
# 它们没有冒号却同样占一大片屏幕 —— 以前完全折不了。
# 收尾括号行刻意留在折叠区**外面**，折起来还能看出这段是什么结束的。


def 括号区(源, 行号):
    编10 = 新编(源)
    return 编10, 编10.折叠区(编10.document().findBlockByNumber(行号))


编a, 区a = 括号区("x = [\n    1,\n    2,\n]\n", 0)
检("列表跨行可折", 区a == 2, "区=%r" % (区a,))
检("收尾括号 ] 露在折叠区外", 区a is not None and 区a < 3)

编b, 区b = 括号区('d = {\n    "a": 1,\n}\n', 0)
检("字典跨行可折", 区b == 1, "区=%r" % (区b,))

编c, 区c = 括号区("核说(\n    1,\n    2,\n)\n", 0)
检("跨行调用可折", 区c == 2, "区=%r" % (区c,))

编d, 区d = 括号区("核说(1)\nx = 1\n", 0)
检("单行括号不折", 区d is None, "区=%r" % (区d,))

编e, 区e = 括号区('x = "("\n核说(1)\n', 0)
检("字符串里的括号不算开括号", 区e is None, "区=%r" % (区e,))

编f, 区f = 括号区("x = 1 核核 ] 注释里\n", 0)
检("注释里的括号不算", 区f is None, "区=%r" % (区f,))

编g, 区g = 括号区("x = ［\n    1,\n］\n", 0)
检("全角方括号可折", 区g == 1, "区=%r" % (区g,))

编g2, 区g2 = 括号区("x = 【\n    1,\n】\n", 0)
检("方头括号【】可折", 区g2 == 1, "区=%r" % (区g2,))

编h, 区h = 括号区("x = [\n    1,\n    2]\n", 0)
检("配平与内容同行时整行留在外面", 区h == 2, "区=%r" % (区h,))

编i, 区i = 括号区("d = {\n    \"a\": [\n        1,\n    ],\n}\n", 0)
检("嵌套括号折到最外层配平前", 区i == 3, "区=%r" % (区i,))

print("== 十二、括号折叠真的把中间行藏起来 ==")
编j = 新编("x = [\n    1,\n    2,\n]\n核说(x)\n")
编j.切换折叠(编j.document().findBlockByNumber(0))
应用.processEvents()
表 = 编j._可见表
检("头行可见", 表[0] is True)
检("中间两行藏起来", 表[1] is False and 表[2] is False)
检("收尾行 ] 仍可见", 表[3] is True)
检("折起来后仍算 1 个折叠", 编j._折叠数 == 1, "折叠数=%r" % 编j._折叠数)
编j.全部展开()
应用.processEvents()
检("全部展开后全部可见", all(编j._可见表))

print("== 十三、冒号块与括号块能共存 ==")
编k = 新编("核定义 f()：\n    核说(1)\n    核说(2)\nx = [\n    1,\n    2,\n]\n")
编k.切换折叠(编k.document().findBlockByNumber(0))
编k.切换折叠(编k.document().findBlockByNumber(3))
应用.processEvents()
检("两种折叠同时生效", 编k._折叠数 == 2, "折叠数=%r" % 编k._折叠数)
表k = 编k._可见表
检("冒号块体藏起", 表k[1] is False and 表k[2] is False)
检("括号块体藏起", 表k[4] is False and 表k[5] is False)
检("括号收尾行仍可见", 表k[6] is True)

print("== 十四、跨行三引号串能独立折叠 ==")
# 以前只有冒号块和括号块两种，三引号串**完全折不了** —— 而长文档、
# 大段 SQL / 提示词 / 帮助文本这些整块塞在串里的场景很常见。
# 更糟的是当时没有「这一行在串里」的概念：串内容里单独一行 `(` 会被
# 当成跨行括号块的开头，折起来把后面整段代码藏掉 —— 假的折叠区。

三双 = '"' * 3


def 三引号区(源, 行号):
    编11 = 新编(源)
    return 编11, 编11.折叠区(编11.document().findBlockByNumber(行号))


编l, 区l = 三引号区('x = %s\n甲\n乙\n%s\n核说(x)\n' % (三双, 三双), 0)
检("裸三引号串可折", 区l == 2, "区=%r" % (区l,))
检("纯收尾行留在折叠区外", 区l is not None and 区l < 3, "区=%r" % (区l,))

编m, 区m = 三引号区('x = 核%s\n甲\n乙\n%s\n' % (三双, 三双), 0)
检("核前缀三引号串可折", 区m == 2, "区=%r" % (区m,))

编n, 区n = 三引号区('x = %s\n甲\n乙%s\n核说(x)\n' % (三双, 三双), 0)
检("收尾与内容同行时整行纳入", 区n == 2, "区=%r" % (区n,))

编o, 区o = 三引号区('x = %sabc%s\n核说(x)\n' % (三双, 三双), 0)
检("单行三引号不折", 区o is None, "区=%r" % (区o,))

编q, 区q = 三引号区("x = %s\n甲\n乙\n%s\n" % ("'" * 3, "'" * 3), 0)
检("单引号三引号串也可折", 区q == 2, "区=%r" % (区q,))

print("== 十五、串里的括号/冒号不算结构（0.2.6 修）==")
# 这两条是本次改动真正的守门断言：改之前 编r 折叠区是 3（假块），
# 编号会 Multi-line 跨行括号折叠，把后面的代码整段藏起来。
编r, 区r = 三引号区('x = %s\n(\n%s\n核说(1)\n' % (三双, 三双), 1)
检("串内单独一行 ( 不产生括号块", 区r is None, "区=%r" % (区r,))

编s, 区s = 三引号区('x = %s\n核若 a：\n%s\n' % (三双, 三双), 1)
检("串内冒号行不产生冒号块", 区s is None, "区=%r" % (区s,))

# 三引号串折叠后，串里的内容必须真的藏起来，收尾行仍可见
编t = 新编('x = %s\n甲\n乙\n%s\n核说(x)\n' % (三双, 三双))
编t.切换折叠(编t.document().findBlockByNumber(0))
应用.processEvents()
表t = 编t._可见表
检("三引号串头行可见", 表t[0] is True)
检("串内容两行藏起来", 表t[1] is False and 表t[2] is False)
检("收尾引号行仍可见", 表t[3] is True)
检("串折起来后仍算 1 个折叠", 编t._折叠数 == 1, "折叠数=%r" % 编t._折叠数)
编t.全部展开()
应用.processEvents()
检("展开后全部可见", all(编t._可见表))

print("== 十六、函数 docstring 与外层函数块各自独立 ==")
# docstring 自己可折，外层 `核定义` 冒号块也可折，两者不能互相吃掉。
编u = 新编('核定义 f()：\n    %s说明\n    第二行\n    %s\n    核返回 1\n' % (三双, 三双))
du = 编u.document()
检("docstring 自身可折", 编u.可折叠(du.findBlockByNumber(1)))
检("docstring 折到第 2 行", 编u.折叠区(du.findBlockByNumber(1)) == 2,
   "区=%r" % (编u.折叠区(du.findBlockByNumber(1)),))
检("外层函数块仍折到第 4 行", 编u.折叠区(du.findBlockByNumber(0)) == 4,
   "区=%r" % (编u.折叠区(du.findBlockByNumber(0)),))

print("== 十七、置文本后三引号缓存必须整份作废（0.2.7 修）==")
# _串态表 做增量重算时靠 _编辑块 决定「从哪一块往后重扫」。
# 而 置文本 期间 _文本变化 被 _载入中 挡住，_编辑块 停在旧值上 ——
# 若新文本块数**恰好与旧文本相同**，增量会从错误位置开始，
# 前面的块继续沿用旧内容的引号结论，折叠区就会错乱。
#
# 这个用例必须让三件事同时成立才能暴露问题（缺一不可）：
#   1. 新旧文本块数相同 —— 否则 len(表) != 块数 会触发全量重算，掩盖问题；
#   2. 旧文本的 _编辑块 落在靠后位置 —— 增量只重扫它后面那些块；
#   3. 旧文本前半段「在串内」、新文本前半段「不在串内」—— 结论相反。
Q3 = '"' * 3
编v = 新编("x = %s\n甲\n乙\n丙\n%s\n尾\n" % (Q3, Q3))
应用.processEvents()
# 先把缓存**建立起来**（否则第一次 置文本 后缓存还是 None，
# 后面那次替换会走「全量重算」分支，测不出作废逻辑）。
_旧表 = 编v._串态表()
检("旧文本已建立串态缓存", any(x is not None for x in _旧表),
   "串态表=%r" % (_旧表,))
# 在末块打字（把 _编辑块 推到 5，且块数不变）
_末 = 编v.document().blockCount() - 1
_尾块 = 编v.document().findBlockByNumber(_末)
_游 = QTextCursor(_尾块)
_游.movePosition(QTextCursor.EndOfBlock)
编v.setTextCursor(_游)
应用.processEvents()
_游.insertText("z")
应用.processEvents()
检("旧文本 _编辑块 已推到末块",
   getattr(编v, "_编辑块", -1) == _末,
   "_编辑块=%r 末块=%r" % (getattr(编v, "_编辑块", None), _末))

# 整份换成同样 6 行、但完全没有三引号的文本（块数不变！）
编v.置文本("a = 1\nb = 2\nc = 3\nd = 4\ne = 5\nf = 6\n")
应用.processEvents()
_表 = 编v._串态表()
_残留 = [i for i, x in enumerate(_表) if x is not None]
检("置文本后三引号串态全部清零", not _残留,
   "第 %r 块残留旧结论，串态表=%r" % (_残留, _表))
_可折 = [i for i in range(编v.document().blockCount())
        if 编v.可折叠(编v.document().findBlockByNumber(i))]
检("置文本后新内容不该有可折块", not _可折, "可折块=%r" % (_可折,))

print()
print("== 全部折叠的性能（P1-3）==")
# 回归：_串态表 曾经每被调用一次就从 _编辑块 重扫到文末。
# 全部折叠 要对每一块调 可折叠 → 折叠区 → _本行括号净值 → _起始串
# → _串态表，n 块就是 n 次全文扫描，合起来 O(n²)。
# 实测修复前 500/1000/2000/4000 行 = 1.79s / 7.21s / 29.50s / 121.31s，
# 8000 行超过 10 分钟 —— 点一下「全部折叠」整个窗口就冻住了。
# 修法：给 _串态表 加「有效水位」，扫完一趟把脏标记清掉，重复调用直接命中。
import time as _时间  # noqa: E402


def _造(行数):
    行集 = []
    for i in range(行数):
        行集.append("核若 核对：" if i % 10 == 0 else "    核说(%d)" % i)
    return "\n".join(行集)


# 门限按「同一台机器上的相对基准」给，真正的回归是 O(n²) 时的秒级/分钟级。
#
# **单次 wall-clock 不能直接判死**（P2-4）：第一次完整回归时 4000 行
# 跑出 201.9 ms，正好越过 200 ms 的门限报失败；紧接着单独复跑 6 次都是
# 158–162 ms，第二次完整回归也过了。也就是说旧门限只有约 1.25 倍余量，
# 机器上任何一个后台任务都能让它假失败，那种「红灯」没有任何信息量。
#
# 现在每档跑 _取样 次，取**中位数**判定（中位数不受单次抖动影响），
# 门限同时放宽到实测值的 2 倍以上。真的退化成 O(n²) 时是几十秒到几分钟，
# 离这些门限差着两三个数量级，不会被放过。
_取样 = 3


def _折叠耗时(行数):
    编 = 新编(_造(行数))
    起 = _时间.perf_counter()
    编.全部折叠()
    耗 = (_时间.perf_counter() - 起) * 1000
    编.已改 = False
    窗.关闭文档(编, 强制=True)
    return 耗


for _行数, _门 in ((500, 60), (1000, 100), (2000, 160), (4000, 320), (8000, 700)):
    _样本 = sorted(_折叠耗时(_行数) for _ in range(_取样))
    _中位 = _样本[len(_样本) // 2]
    检(
        "全部折叠 %d 行 中位 ≤ %d ms（中位 %.1f，各次 %s）"
        % (_行数, _门, _中位, "/".join("%.0f" % x for x in _样本)),
        _中位 <= _门,
        "%.1f ms 超过门限 %d ms" % (_中位, _门),
    )

# 语义不许变：可折叠块数必须等于实际折起数
_编 = 新编(_造(2000))
_编.全部折叠()
_块 = _编.document().firstBlock()
_数 = 0
while _块.isValid():
    if _编.可折叠(_块):
        _数 += 1
    _块 = _块.next()
检("全部折叠后 可折叠块数 == 实际折起数（%d）" % _数, _数 == _编._折叠数,
   "可折叠 %d，实际折起 %d" % (_数, _编._折叠数))

# 缓存必须真的命中：没有任何改动的连续调用不该重新扫全文
_编 = 新编(_造(2000))
_编._串态表()
_起 = _时间.perf_counter()
for _ in range(50):
    _编._串态表()
_全程 = (_时间.perf_counter() - _起) * 1000
检("无改动时 _串态表 50 次调用 ≤ 5 ms（实测 %.2f ms）" % _全程, _全程 <= 5,
   "%.2f ms —— 说明水位没生效，还在每次重扫" % _全程)

# 改动之后必须能看见新结论（水位不能把缓存焊死）
_编 = 新编('甲 = """\n内容\n"""\n核说(1)')
_编._串态表()
_块1 = _编.document().findBlockByNumber(1)
检("块1 起始处于三引号串内", _编._起始串(_块1) == '"""',
   repr(_编._起始串(_块1)))
# 把首行的三引号删掉 → 第 1 块不再处于串内
_游 = QTextCursor(_编.document().findBlockByNumber(0))
_游.movePosition(QTextCursor.EndOfBlock)
_编.setTextCursor(_游)
_编.insertPlainText("\n")   # 触发 _文本变化 → 标脏
_编.undo()
应用.processEvents()
检("改动并回退后 串态仍自洽", _编._起始串(_块1) == '"""',
   repr(_编._起始串(_块1)))

print()
print("== 折叠三角不许压住行号 ==")
# 回归：行号栏左边只留了 8px，而三角画在 2~16（大字号更宽），
# 行号右对齐后左端恰好落在 8 —— 第一位数字被三角盖住。
# 实测 9/12/16/22/30/40 号字全部重叠，40 号字压掉 14px。
_编g = 新编("核定义 f():\n    核说(1)\n" * 60)
for _字号 in (9, 12, 16, 22, 30, 40):
    窗.设字号(_字号)
    应用.processEvents()
    _栏 = _编g.行号
    _栏.按行号调整宽度(_编g.document().blockCount())
    _位 = max(3, len(str(_编g.document().blockCount())))
    _数字宽 = _栏.fontMetrics().horizontalAdvance("8" * _位)
    _数字左 = _栏.宽度 - 10 - _数字宽
    _高 = int(_编g.blockBoundingRect(_编g.document().firstBlock()).height())
    _半 = max(3, min(int(_高 * 0.22), max(3, (_栏.折叠栏宽 - 4) // 2)))
    _左 = max(2, (_栏.折叠栏宽 - _半 * 2) // 2)
    _三角右 = _左 + _半 * 2
    检("字号%d：三角右缘 %d < 行号左端 %d" % (_字号, _三角右, _数字左),
       _三角右 <= _数字左,
       "栏宽%d 折叠栏%d 行高%d" % (_栏.宽度, _栏.折叠栏宽, _高))
    检("字号%d：三角落在折叠栏内（点击判定同一口径）" % _字号,
       _三角右 <= _栏.折叠栏宽,
       "三角右%d 折叠栏%d" % (_三角右, _栏.折叠栏宽))
窗.设字号(12)
应用.processEvents()

print()
print("=" * 62)
if 问题:
    for 说明, _ in 问题:
        print("  · %s" % 说明)
    sys.exit(1)
print("代码折叠全部正常")
