# -*- coding: utf-8 -*-
"""版本控制面板：只读 diff 视图。

要点：
  · 面板**仍然只读** —— 不能有暂存/提交/推送的入口（推送有硬约定）；
  · 点一行能看到那个文件的 diff，不是只有文件名；
  · 未跟踪文件也要能看到内容（git diff 对它们完全不出声）；
  · 已暂存的改动要能看到暂存区相对 HEAD 的差异；
  · diff 的增/删行上色，且换主题后颜色要跟着换（字符格式不会自动跟着 QSS 走）；
  · 大 diff 要截断，不能把几万行塞进文本框卡住界面；
  · 没有 git、不是仓库时面板要降级，不崩。

用法：python 测试/查版本面板.py
"""

import os
import shutil
import subprocess
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("核工坊_配置目录", tempfile.mkdtemp(prefix="核工坊版本面板_"))

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication  # noqa: E402

import 核工坊Qt  # noqa: E402
import 版本控制  # noqa: E402
import 版本控制窗口  # noqa: E402

应用 = QApplication.instance() or QApplication(sys.argv)
主 = 核工坊Qt.主窗()

问题 = []


def 检(说明, 条件, 详情=""):
    if 条件:
        print("  OK  %s" % 说明)
    else:
        问题.append((说明, 详情))
        print("  !! %s" % 说明)
        if 详情:
            print("       %s" % 详情)


def 有git():
    return 版本控制.找git() is not None


def 造仓库():
    """建一个真的 git 仓库，带三种状态的改动。"""
    目录 = tempfile.mkdtemp(prefix="核工坊面板仓库_")

    def git(*参数):
        subprocess.run(
            [版本控制.找git(), "-C", 目录] + list(参数),
            capture_output=True,
            timeout=30,
            creationflags=版本控制.无窗口标志(),
        )

    git("init")
    git("config", "user.email", "测试@example.com")
    git("config", "user.name", "测试")
    # 改名要用到，先给一个稳定的默认分支名
    git("checkout", "-b", "main")

    改过 = os.path.join(目录, "改过.xht")
    with open(改过, "w", encoding="utf-8") as f:
        f.write("核说(1)\n核说(2)\n")
    跟踪 = os.path.join(目录, "跟踪.xht")
    with open(跟踪, "w", encoding="utf-8") as f:
        f.write("核说(旧)\n")
    git("add", ".")
    git("commit", "-m", "初始")

    # 1) 工作区已修改
    with open(改过, "w", encoding="utf-8") as f:
        f.write("核说(1)\n核说(3)\n")
    # 2) 已暂存的改动
    with open(跟踪, "w", encoding="utf-8") as f:
        f.write("核说(新)\n")
    git("add", "跟踪.xht")
    # 3) 未跟踪的新文件
    新的 = os.path.join(目录, "新来的.xht")
    with open(新的, "w", encoding="utf-8") as f:
        f.write("核说(未跟踪)\n")
    return 目录


def _等到(窗, 期望行数=None):
    """让单发的延后任务真的跑一轮 —— 读 diff 是 QTimer(0) 排的。"""
    for _ in range(5):
        应用.processEvents()


# ---------------------------------------------------------------------------

print("== 一、只读：面板里没有任何写操作入口 ==")
源码 = open(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "版本控制窗口.py"),
    encoding="utf-8",
).read()
# 「暂存」「提交」这些词在面板源码里只应出现在说明文字中（比如
# 「本面板只做展示，暂存/提交请去 git 客户端」），绝不能是命令调用。
# 所以判据不是「有没有这个词」，而是「有没有 subprocess 调用这些子命令」。
检("面板里没有任何 subprocess 调用", "subprocess" not in 源码)
检("面板里没有 git 命令拼接", '"git"' not in 源码 and '"add"' not in 源码)
检(
    "版本控制.py 没有实现提交/推送函数",
    not any(名 in dir(版本控制) for 名 in ("提交", "推送", "暂存")),
)
# 取差异 里只该出现只读子命令。直接扫源码里 _跑(...) 用到的参数词。
控制源码 = open(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "版本控制.py"),
    encoding="utf-8",
).read()
写命令 = [名 for 名 in ("add", "commit", "push", "reset", "checkout", "merge", "rebase", "stash")]
检(
    "版本控制.py 里没有任何写操作的子命令",
    not any(('"%s"' % 名) in 控制源码 for 名 in 写命令),
    "命中=%r" % [名 for 名 in 写命令 if ('"%s"' % 名) in 控制源码],
)

print("== 二、取差异：四种状态都要有内容 ==")
if not 有git():
    print("  --  跳过：这台机器上没有 git")
else:
    目录 = 造仓库()

    文本, 说明 = 版本控制.取差异(目录, "改过.xht")
    检("已修改的文件能取到 diff", bool(文本), repr(说明))
    检("diff 里有减号行", any(l.startswith("-") for l in 文本.splitlines()))
    检("diff 里有加号行", any(l.startswith("+") for l in 文本.splitlines()))

    文本2, 说明2 = 版本控制.取差异(目录, "跟踪.xht")
    检("已暂存的文件能取到 diff", bool(文本2), repr(说明2))
    检("暂存态给了说明", "暂存" in 说明2, repr(说明2))

    文本3, 说明3 = 版本控制.取差异(目录, "新来的.xht")
    检("未跟踪文件能看到内容", "核说(未跟踪)" in 文本3, repr(文本3[:60]))
    检("未跟踪的文件头按新增格式", "--- /dev/null" in 文本3, repr(文本3[:60]))

    文本4, 说明4 = 版本控制.取差异(目录, "根本不存在.xht")
    检("不存在的文件给说明而不是崩溃", not 文本4 and bool(说明4), repr(说明4))

    大 = os.path.join(目录, "巨大.xht")
    with open(大, "w", encoding="utf-8") as f:
        for i in range(版本控制.diff行数上限 + 500):
            f.write("核说(%d)\n" % i)
    文本5, 说明5 = 版本控制.取差异(目录, "巨大.xht")
    行数5 = len(文本5.splitlines())
    检(
        "未跟踪的超大文件被截断",
        "已截断" in 文本5 and 行数5 <= 版本控制.diff行数上限 + 10,
        "行数=%d 说明=%r" % (行数5, 说明5),
    )


print("== 三、面板界面：选中就能看到 diff ==")
if not 有git():
    print("  --  跳过：这台机器上没有 git")
else:
    窗 = 版本控制窗口.版本控制窗口(主, 目录)
    检("面板有 diff 视图", hasattr(窗, "差异"))
    检("diff 视图是只读的", 窗.差异.isReadOnly())
    检("面板跟主题走", getattr(窗, "跟主题", False))
    检("列出的改动不是空的", 窗.树.topLevelItemCount() >= 3, "行数=%d" % 窗.树.topLevelItemCount())

    # 选中第一行（已修改那个）
    窗.树.setCurrentItem(窗.树.topLevelItem(0))
    _等到(窗)
    内容 = 窗.差异.toPlainText()
    检("选中后 diff 视图有内容", bool(内容.strip()), repr(内容[:60]))
    检("diff 视图里有增删行", "-核说(2)" in 内容 or "+核说(3)" in 内容, repr(内容[:120]))

    # 增量：换一行，内容要跟着换
    窗.树.setCurrentItem(窗.树.topLevelItem(1))
    _等到(窗)
    内容2 = 窗.差异.toPlainText()
    检("换一行后 diff 内容变了", 内容2 != 内容, repr(内容2[:60]))

    print("== 四、上色与换主题 ==")
    # 数一数不同颜色的增/删行
    文档 = 窗.差异.document()
    色集 = set()
    块 = 文档.firstBlock()
    while 块.isValid():
        文本 = 块.text()
        if 文本.startswith(("+", "-")):
            片段 = 块.begin()
            色集.add(片段.fragment().charFormat().foreground().color().name())
        块 = 块.next()
    检("增/删行有两种以上颜色", len(色集) >= 2, "颜色=%r" % (色集,))

    主.换主题("浅色")
    应用.processEvents()
    窗.树.setCurrentItem(窗.树.topLevelItem(0))
    _等到(窗)
    新集 = set()
    块 = 窗.差异.document().firstBlock()
    while 块.isValid():
        文本 = 块.text()
        if 文本.startswith(("+", "-")):
            片段 = 块.begin()
            新集.add(片段.fragment().charFormat().foreground().color().name())
        块 = 块.next()
    检("换主题后 diff 行颜色跟着变", 新集 != 色集, "深色=%r 浅色=%r" % (色集, 新集))
    主.换主题("深色")
    应用.processEvents()
    窗.close()

print("== 五、已跟踪的超大改动也截断 ==")
if not 有git():
    print("  --  跳过：这台机器上没有 git")
else:
    # 先提交大文件，再整体改写 → 走 git diff 那条路（不是未跟踪路径）
    subprocess.run(
        [版本控制.找git(), "-C", 目录, "add", "巨大.xht"],
        capture_output=True,
        timeout=30,
        creationflags=版本控制.无窗口标志(),
    )
    subprocess.run(
        [版本控制.找git(), "-C", 目录, "commit", "-m", "大文件"],
        capture_output=True,
        timeout=30,
        creationflags=版本控制.无窗口标志(),
    )
    with open(大, "w", encoding="utf-8") as f:
        for i in range(版本控制.diff行数上限 + 500):
            f.write("核说(%d 改)\n" % i)
    文本6, 说明6 = 版本控制.取差异(目录, "巨大.xht")
    行数6 = len(文本6.splitlines())
    检(
        "已跟踪的超大改动被截断",
        "已截断" in 文本6 and 行数6 <= 版本控制.diff行数上限 + 10,
        "行数=%d 说明=%r" % (行数6, 说明6),
    )

print("== 六、没有 git / 不是仓库时降级 ==")
空目录 = tempfile.mkdtemp(prefix="核工坊空目录_")
窗2 = 版本控制窗口.版本控制窗口(主, 空目录)
检("非仓库时不崩", 窗2.树.topLevelItemCount() == 0)
检("非仓库时给了原因", bool(窗2.概要.text()), repr(窗2.概要.text()))
窗2.close()

print()
print("=" * 62)
if 问题:
    print("发现 %d 个问题：" % len(问题))
    for 说明, _ in 问题:
        print("  · %s" % 说明)
    sys.exit(1)
print("版本控制面板全部正常")
