# -*- coding: utf-8 -*-
"""版本控制接入验证（只读）。

要点：
  · 仓库里能读到分支和改动；非仓库要降级成「未启用」而不是报错；
  · 中文路径不能变成 \346\240\270 那种八进制转义；
  · 面板和顶行按钮都要能刷新；
  · 绝不能真的执行提交/推送 —— 这里连命令都不该发出。

用法：python 测试/查版本控制.py
"""

import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("核工坊_配置目录", tempfile.mkdtemp(prefix="核工坊版本_"))

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication  # noqa: E402

import 版本控制  # noqa: E402
import 核工坊Qt  # noqa: E402

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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


print("== 一、git 探测 ==")
git = 版本控制.找git()
检("找到 git 可执行文件", bool(git), "git=%r" % git)

print("== 二、仓库目录 ==")
真实 = os.path.join(根, "版本控制.py")
s = 版本控制.状态(根)
检("识别为可用仓库", s["可用"], "原因=%r" % s.get("原因"))
检("读到分支名", bool(s["分支"]), "分支=%r" % s["分支"])
检("改动是列表", isinstance(s["改动"], list))
检("摘要格式正确", s["可用"] and s["摘要" if False else "分支"] in 版本控制.摘要(s),
   "摘要=%r" % 版本控制.摘要(s))
print("      摘要：%s" % 版本控制.摘要(s))

print("== 三、中文路径不能被转义成八进制 ==")
中文改动 = [p for _, p in s["改动"] if p.endswith(".py")]
八进制 = [p for _, p in s["改动"] if "\\3" in p or "\\4" in p]
检("没有八进制转义路径", not 八进制, "可疑：%r" % 八进制[:3])
if 中文改动:
    print("      样例：%r" % 中文改动[0])

print("== 四、非仓库目录要降级 ==")
s2 = 版本控制.状态(os.path.join(tempfile.gettempdir()))
检("非仓库 → 不可用", not s2["可用"], "可用=%r" % s2["可用"])
检("给出了原因", bool(s2.get("原因")), "原因=%r" % s2.get("原因"))
检("摘要显示未启用", "未启用" in 版本控制.摘要(s2), "摘要=%r" % 版本控制.摘要(s2))
s3 = 版本控制.状态("")
检("空路径不崩", isinstance(s3, dict) and not s3["可用"])
s4 = 版本控制.状态(os.path.join(tempfile.gettempdir(), "绝对不存在的目录_x9"))
检("不存在目录不崩", isinstance(s4, dict) and not s4["可用"])

print("== 五、状态码翻译（两列含义不同）==")
for 码, 期望 in (
    ("??", "未跟踪"),
    (" M", "已修改"),      # 工作区改了，没暂存
    ("M ", "已暂存"),      # 暂存区里有改动
    ("MM", "已暂存"),      # 两处都改了，按暂存区说
    (" D", "已删除"),
    ("A ", "新增已暂存"),
    ("UU", "冲突"),
    ("!!", "已忽略"),
):
    说明, _色 = 版本控制.说明状态(码)
    检("%r → %s" % (码, 期望), 说明 == 期望, "实际 %r" % 说明)

print("== 六、主窗按钮与面板 ==")
窗.刷新版本状态()
文字 = 窗.顶行.版本钮.text()
检("顶行按钮文字已更新", 文字 != "" and ("⎇" in 文字), "文字=%r" % 文字)
检("按钮不再是死占位", "尚未接入" not in 窗.顶行.版本钮.toolTip(),
   "提示=%r" % 窗.顶行.版本钮.toolTip())
print("      按钮：%r　提示：%r" % (文字, 窗.顶行.版本钮.toolTip()))

try:
    import 版本控制窗口

    面板 = 版本控制窗口.版本控制窗口(窗, 根)
    应用.processEvents()
    行数 = 面板.树.topLevelItemCount()
    检("面板能构造", True)
    检("面板列数与仓库改动一致", 行数 == len(s["改动"]),
       "面板 %d 行 / 状态 %d 项" % (行数, len(s["改动"])))
    检("概要非空", bool(面板.概要.text()), "概要=%r" % 面板.概要.text())
    面板.刷新()
    检("刷新后仍正常", 面板.树.topLevelItemCount() == 行数)
    面板.close()
    面板.deleteLater()
except Exception as e:  # noqa: BLE001
    检("面板能构造", False, repr(e))

print("== 七、非仓库时面板要给提示 ==")
try:
    面板2 = 版本控制窗口.版本控制窗口(窗, tempfile.gettempdir())
    检("非仓库面板能构造", True)
    检("非仓库面板给了提示", "未启用" in 面板2.概要.text(), 面板2.概要.text())
    检("非仓库面板列出 0 行", 面板2.树.topLevelItemCount() == 0)
    面板2.close()
    面板2.deleteLater()
except Exception as e:  # noqa: BLE001
    检("非仓库面板能构造", False, repr(e))

print("== 八、绝不能有写操作（只读保证）==")
源码 = open(os.path.join(根, "版本控制.py"), encoding="utf-8").read()
危险 = ["commit", "push", "add", "checkout", "reset", "clean", "stash", "merge",
        "rebase", "rm ", "fetch", "pull", "tag"]
命中 = []
for 词 in 危险:
    # 只看真正拼进命令列表的地方
    if '"%s"' % 词 in 源码 or "'%s'" % 词 in 源码:
        命中.append(词)
检("源码里没有写操作命令", not 命中, "命中：%r" % 命中)

print()
print("=" * 62)
if 问题:
    print("发现 %d 个问题：" % len(问题))
    for 说明, _ in 问题:
        print("  · %s" % 说明)
    sys.exit(1)
print("版本控制接入全部正常")
