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

print()
print("=" * 62)
if 问题:
    print("发现 %d 个问题：" % len(问题))
    for 说明, _ in 问题:
        print("  · %s" % 说明)
    sys.exit(1)
print("代码折叠全部正常")
