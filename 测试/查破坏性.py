# -*- coding: utf-8 -*-
"""破坏性 bug 回归：用户的数据绝不能悄悄消失。

这里每一条都是**实测踩到过的**破坏性 bug，不是假想。
每个用例都先复现、再断言「修好了」。

覆盖：
  1. 关窗口（Alt+F4 / 任务栏关闭）必须问要不要保存
  2. 保存必须是**原子写** —— 写失败时原文件还在
  3. 核 转译 -o 指向源文件本身要拦下来
  4. 未定义清单的保存也是原子写
  5. 切换注释不能改到字符串里的内容
  6. 切换注释不能给已经有注释的行套第二层

用法：python 测试/查破坏性.py
"""

import os
import shutil
import stat
import subprocess
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("核工坊_配置目录", tempfile.mkdtemp(prefix="核工坊破坏性_"))

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

import 核  # noqa: E402
import 核工坊Qt  # noqa: E402

应用 = QApplication.instance() or QApplication(sys.argv)
窗 = 核工坊Qt.主窗()

问题 = []


def 检(说明, 条件, 详情=""):
    if 条件:
        print("  OK  %s" % 说明)
    else:
        问题.append(说明)
        print("  !! %s" % 说明)
        if 详情:
            print("        %s" % 详情)


临时 = tempfile.mkdtemp(prefix="核破坏性_")

# ---------------------------------------------------------------------------
print("== 一、关窗口必须问要不要保存 ==")
# 以前 Qt 版**根本没有 closeEvent**：顶栏的 ✕ 按钮走 退出()（有确认），
# 但用户按 Alt+F4、点任务栏的关闭时，Qt 直接把窗口关掉，
# 未保存的修改无声无息全丢。
#
# 现在的实现用**非模态**确认框（QMessageBox.open()），不是模态的
# QMessageBox.question —— 因为在退出流程里弹模态框会把事件循环卡死。
# 所以下面的打桩换成「装上一个假的非模态框」：把 主窗._问要不要保存
# 换成一个记录型函数，再手动触发 closeEvent。
窗.show()
编 = 窗.当前
编.置文本('核说("未保存的内容")', 标记已改=True)

from PySide6.QtCore import QEvent  # noqa: E402
from PySide6.QtGui import QCloseEvent  # noqa: E402


def 发关窗事件():
    """真的给主窗发一个 Close 事件 —— 走的是 closeEvent 那条路。"""
    应用.sendEvent(窗, QCloseEvent())


问过 = []
原问 = 核工坊Qt.主窗._问要不要保存


def 装桩(答案):
    def 桩(self):
        问过.append(1)
        # 模拟用户选「取消」：只是把标志复位，窗口重新显示
        if 答案 == QMessageBox.Cancel:
            self._关窗确认中 = False
            self.showNormal()
    return 桩


# —— 选「取消」：窗口要留着 ——
核工坊Qt.主窗._问要不要保存 = 装桩(QMessageBox.Cancel)
try:
    窗.show()
    发关窗事件()
    应用.processEvents()
    检("选「取消」时窗口不关", 窗.isVisible())
    检("选「取消」时确实问过", len(问过) >= 1, "问了 %d 次" % len(问过))

    # —— 没改动的文档不该打扰用户 ——
    问过.clear()
    for d in 窗.文档集:
        d.已改 = False
    发关窗事件()
    应用.processEvents()
    检("没有改动时不问", len(问过) == 0, "问了 %d 次" % len(问过))
finally:
    核工坊Qt.主窗._问要不要保存 = 原问
    for d in 窗.文档集:
        d.已改 = False

# ---------------------------------------------------------------------------
print("== 二、保存必须是原子写 ==")
# 以前是 open(路径, "w") —— 先把原文件清空再写。
# 写到一半崩了 / 磁盘满了 / 断电，用户的代码就没了。
目录 = tempfile.mkdtemp(prefix="核原子写_")
路径 = os.path.join(目录, "a.xht")
with open(路径, "w", encoding="utf-8") as f:
    f.write("原始内容\n")

窗2 = 核工坊Qt.主窗()
窗2.新建()
编2 = 窗2.当前
编2.文件路径 = 路径
编2.置文本("新的内容\n", 标记已改=True)
检("保存成功", 窗2.保存(编2, 弹窗=False))
with open(路径, encoding="utf-8") as f:
    检("内容已更新", f.read() == "新的内容\n")
检(
    "没有留下临时文件",
    not [n for n in os.listdir(目录) if "tmp" in n],
    repr(os.listdir(目录)),
)

# 把目标文件设成只读：写会失败，但**原内容必须还在**
只读 = os.path.join(目录, "只读.xht")
with open(只读, "w", encoding="utf-8") as f:
    f.write("不能被破坏的内容\n")
os.chmod(只读, stat.S_IREAD)
编2.文件路径 = 只读
编2.置文本("要被拒绝的写入\n", 标记已改=True)
保存成功 = 窗2.保存(编2, 弹窗=False)
检("只读文件保存失败（返回 False）", not 保存成功)
try:
    with open(只读, encoding="utf-8") as f:
        内容 = f.read()
except OSError:
    内容 = "<读不出来>"
检("只读文件的原内容还在", 内容 == "不能被破坏的内容\n", repr(内容))
os.chmod(只读, stat.S_IWRITE)

# ---------------------------------------------------------------------------
print("== 二之二、另存为覆盖已有文件要确认 ==")
# 覆盖是破坏性的。系统的「另存为」对话框一般会自己问，但那是原生对话框的
# 行为 —— Qt 用非原生实现时不问，静默覆盖就没了。
import PySide6.QtWidgets as W  # noqa: E402

已有 = os.path.join(目录, "b.xht")
with open(已有, "w", encoding="utf-8") as f:
    f.write("别人的重要代码\n")
编2.文件路径 = None
编2.置文本("我的新代码\n", 标记已改=True)

原选框 = W.QFileDialog.getSaveFileName
原问题框 = QMessageBox.question
W.QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (已有, ""))
try:
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.No)
    检("回答「不」时不覆盖", not 窗2.另存为(编2))
    with open(已有, encoding="utf-8") as f:
        检("原文件内容还在", f.read() == "别人的重要代码\n")

    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
    检("回答「是」时才覆盖", 窗2.另存为(编2))
    with open(已有, encoding="utf-8") as f:
        检("内容已更新", f.read() == "我的新代码\n")
finally:
    W.QFileDialog.getSaveFileName = 原选框
    QMessageBox.question = 原问题框

# ---------------------------------------------------------------------------
print("== 三、核 转译 -o 不能默默盖掉源文件 ==")
内核脚本 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "核.py")
源 = os.path.join(目录, "源.xht")
with open(源, "w", encoding="utf-8") as f:
    f.write("核说(1)\n")


def 跑核(*参数):
    结果 = subprocess.run(
        [sys.executable, 内核脚本, *参数],
        capture_output=True,
        env=dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1"),
        timeout=60,
    )
    return (
        结果.returncode,
        (结果.stdout or b"").decode("utf-8", "replace"),
        (结果.stderr or b"").decode("utf-8", "replace"),
    )


码, 出, 错 = 跑核("转译", 源, "-o", 源)
检("不写 --覆盖 时拒绝", 码 != 0, "码=%r" % 码)
检("给了中文提示", "覆盖" in (出 + 错), repr((出 + 错)[:200]))
with open(源, encoding="utf-8") as f:
    检("源文件没被动过", f.read() == "核说(1)\n")

码, 出, 错 = 跑核("转译", 源, "-o", 源, "--覆盖")
检("写了 --覆盖 才放行", 码 == 0, "码=%r 错=%r" % (码, 错))

# 普通的 -o 不受影响
目标 = os.path.join(目录, "b.py")
码, 出, 错 = 跑核("转译", 源, "-o", 目标)
检("普通 -o 正常", 码 == 0 and os.path.exists(目标), "码=%r" % 码)

# ---------------------------------------------------------------------------
print("== 四、未定义清单也是原子写 ==")
清单 = os.path.join(目录, "未定义.txt")
报 = 核.取报告(清单)
报.记录("ascii", "内置函数", "a.xht", 1, 1)
报.保存()
with open(清单, encoding="utf-8") as f:
    检("清单写出来了", "ascii" in f.read())
检(
    "没有留下 .tmp",
    not [n for n in os.listdir(目录) if n.endswith(".tmp")],
    repr(os.listdir(目录)),
)

# ---------------------------------------------------------------------------
print("== 五、切换注释不能改到字符串里 ==")
# 多行三引号串的中间几行在语法上是字符串的一部分。
# 在那里插一个「核核 」会直接改掉程序的输出 ——
# 实测：核说(\"\"\"第一行 / # 井号行 / 第三行\"\"\") 切一次就变成
# 「核核 第三行\"\"\"」，程序输出当场变了。
from PySide6.QtGui import QTextCursor  # noqa: E402

窗3 = 核工坊Qt.主窗()
编3 = 窗3.当前


def 切注释(文本):
    编3.置文本(文本)
    游 = 编3.textCursor()
    游.select(QTextCursor.Document)
    编3.setTextCursor(游)
    编3.切换注释()
    return 编3.取文本()


原 = '核说("""第一行\n# 井号行\n第三行""")\n'
切后 = 切注释(原)
检("多行三引号串里的内容没被动", 切后 == 原, "实际 %r" % 切后)

原2 = '核说("核核 在串里")\n'
切后2 = 切注释(原2)
检("单行字符串里的「核核」没被动", 切后2 == 原2, "实际 %r" % 切后2)

# ---------------------------------------------------------------------------
print("== 六、切换注释不能给已有注释的行套第二层 ==")
# 以前判断的是「全是同一种前缀」，混合块会被误判成「要加注释」，
# 给已经有注释的那行再加一层 —— 变成「核核 核核 已有」，
# 之后再也去不掉。
原3 = "核说(1)\n# 已有注释\n核说(2)\n"
切后3 = 切注释(原3)
检("已有注释的行没有被套第二层", "核核 核核" not in 切后3, "实际 %r" % 切后3)
检("代码行加了注释", 切后3.split("\n")[0] == "核核 核说(1)", repr(切后3))
检("原注释行保持原样", 切后3.split("\n")[1] == "# 已有注释", repr(切后3))

原4 = "核说(1)\n核核 已有\n核说(2)\n"
切后4 = 切注释(原4)
检("核核 注释行没被套第二层", "核核 核核" not in 切后4, "实际 %r" % 切后4)

# 往返一次后代码内容必须与原来一样
import re  # noqa: E402


def 剥注释(文本):
    文本 = re.sub(r"核核 ", "", 文本)
    return re.sub(r"# ?", "", 文本)


for 名, t in (
    ("混合块（# 注释）", 原3),
    ("混合块（核核 注释）", 原4),
    ("全 # 注释块", "# 一\n# 二\n"),
    ("全 核核 注释块", "核核 一\n核核 二\n"),
):
    一次 = 切注释(t)
    两次 = 切注释(一次)
    检(
        "%s：往返后代码内容不变" % 名,
        剥注释(两次) == 剥注释(t),
        "原=%r 两次后=%r" % (剥注释(t), 剥注释(两次)),
    )

# ---------------------------------------------------------------------------
print("== 七、「停止」必须真的把子进程杀掉 ==")
# 打包成 exe 之后，运行用户程序的命令是 [核工坊Qt.exe, "--内核", 文件]
# —— 让 exe 自我重新调用。PyInstaller 单文件 exe 是「引导进程 + 应用子进程」
# 两层，只 kill() 引导进程的话，真正跑用户代码的那个会**变成孤儿继续跑**，
# 用户按了停止却发现程序没停，孤儿还锁着 exe 让下次打包失败。
import subprocess as _sp  # noqa: E402
import time as _time  # noqa: E402

窗4 = 核工坊Qt.主窗()
目录4 = tempfile.mkdtemp(prefix="核杀进程_")
死循环 = os.path.join(目录4, "死循环.xht")
with open(死循环, "w", encoding="utf-8") as f:
    f.write("核导入 time\n核循环若 核对：\n    time.sleep(0.05)\n")
e4 = 窗4.打开(死循环)
应用.processEvents()
窗4.运行()
for _ in range(80):
    应用.processEvents()
    _time.sleep(0.05)
    if 窗4.进程 is not None:
        break
if 窗4.进程 is None:
    检("程序真的跑起来了", False, "进程没起来")
else:
    检("程序真的跑起来了", True)
    pid = 窗4.进程.pid
    窗4.停止()
    应用.processEvents()
    _time.sleep(1.2)
    r = _sp.run(
        ["tasklist", "/FI", "PID eq %d" % pid],
        capture_output=True, text=True, errors="replace",
    )
    检("停止后子进程真的没了", str(pid) not in r.stdout, "tasklist 输出还含 pid %d" % pid)
    检("停止后 self.进程 已清空", 窗4.进程 is None)
shutil.rmtree(目录4, ignore_errors=True)

shutil.rmtree(临时, ignore_errors=True)
shutil.rmtree(目录, ignore_errors=True)

print()
print("=" * 62)
if 问题:
    print("发现 %d 处破坏性问题：" % len(问题))
    for 项 in 问题:
        print("  · %s" % 项)
    sys.exit(1)
print("破坏性回归全部通过")
