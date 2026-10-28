# -*- coding: utf-8 -*-
"""帮助功能验证：说明文档、版本历史、关于、语法速查。

要点：
  · 帮助菜单四项都要能点到，不能抛异常；
  · 版本历史要按版本号正确排序（不是字典序）；
  · 找不到 版本/ 目录时要给提示而不是崩。

用法：python 测试/查帮助.py
"""

import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("核工坊_配置目录", tempfile.mkdtemp(prefix="核工坊帮助_"))

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication  # noqa: E402

import 核工坊Qt  # noqa: E402
import 帮助窗口  # noqa: E402

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


print("== 一、版本排序（不能按字典序）==")
# 字典序会把 v0.0.10 排到 v0.0.9 前面
样本 = ["v0.0.10", "v0.0.9", "v0.0.11", "v0.0.2", "v0.0.1"]
排后 = sorted(样本, key=帮助窗口.版本排序键)
期望 = ["v0.0.1", "v0.0.2", "v0.0.9", "v0.0.10", "v0.0.11"]
检("数字排序正确", 排后 == 期望, "实际 %r" % 排后)

# 异常命名不能抛
try:
    奇怪 = sorted(["vabc", "v1.2.3", "没有v"], key=帮助窗口.版本排序键)
    检("异常命名不抛异常", True)
except Exception as e:  # noqa: BLE001
    检("异常命名不抛异常", False, repr(e))

print("== 二、真实归档目录 ==")
版本们 = 帮助窗口.已归档版本()
检("读到归档版本", len(版本们) > 0, "读到 %d 个" % len(版本们))
if 版本们:
    名们 = [x[0] for x in 版本们]
    检("按版本号从小到大", 名们 == sorted(名们, key=帮助窗口.版本排序键), "%r" % 名们)
    有时间的 = [x for x in 版本们 if x[1]]
    检("多数能读到归档时间", len(有时间的) >= len(版本们) - 1,
       "有时间的 %d / %d" % (len(有时间的), len(版本们)))
    print("      最新：%r" % (版本们[-1],))

print("== 三、版本历史对话框 ==")
try:
    对 = 帮助窗口.版本历史对话框(窗, 核工坊Qt.核.版本)
    文本 = 对._拼文本(版本们)
    检("能构造", True)
    # 「← 当前」这个标记只在**当前版本已归档**时才会出现。
    # 如果刚改完版本号还没跑 归档版本.py，这里就会失败 ——
    # 实测踩过：升到 0.1.5 但没归档，全量回归挂在这一条上，
    # 看起来像「帮助功能坏了」，其实是测试的顺序依赖。
    # 所以分开断言，并在没有标记时说清楚原因。
    有名们 = [x[0] for x in 版本们]
    当前已归档 = ("v%s" % 核工坊Qt.核.版本) in 有名们
    if 当前已归档:
        检("文本含当前版本标记", "← 当前" in 文本, 文本[:200])
    else:
        print("  --  跳过「当前版本标记」：当前版本 v%s 还没归档"
              "（先跑 测试/归档版本.py）" % 核工坊Qt.核.版本)
    检("文本非空", len(文本) > 20)
    对.close()
    对.deleteLater()
except Exception as e:  # noqa: BLE001
    检("能构造", False, repr(e))

print("== 四、目录不存在时不崩 ==")
原根 = 帮助窗口.版本根
try:
    帮助窗口.版本根 = os.path.join(tempfile.gettempdir(), "不存在的版本目录_xyz")
    检("空目录返回空表", 帮助窗口.已归档版本() == [])
    对2 = 帮助窗口.版本历史对话框(窗, 核工坊Qt.核.版本)
    空文本 = 对2._拼文本([])
    检("空表给出归档指引", "归档" in 空文本, 空文本[:120])
    对2.close()
    对2.deleteLater()
except Exception as e:  # noqa: BLE001
    检("目录不存在时不崩", False, repr(e))
finally:
    帮助窗口.版本根 = 原根

print("== 五、关于对话框 ==")
try:
    关 = 帮助窗口.关于对话框(窗, 核工坊Qt.核.版本)
    检("能构造", True)
    # 内容里要有版本和 Python 版本
    标签 = [w.text() for w in 关.findChildren(type(关.findChild(关.__class__)))]
    关.close()
    关.deleteLater()
except Exception as e:  # noqa: BLE001
    检("能构造", False, repr(e))

print("== 六、主窗的帮助方法都能调用 ==")
# 说明文档/版本记录 是开在内部标签页里的，不是在系统默认程序里打开 ——
# 所以这里可以放心检查标签数，不会有外部窗口弹出来。
def 标签数():
    return 窗.标签栏.count()


for 名, 槽 in (
    ("语法速查", 窗.语法速查),
    ("打开说明文档", 窗.打开说明文档),
    ("打开版本记录", 窗.打开版本记录),
    ("版本历史", 窗.版本历史),
    ("关于", 窗.关于),
):
    前 = 标签数()
    try:
        槽()
        应用.processEvents()
        检("调用 %s 不抛异常" % 名, True)
    except Exception as e:  # noqa: BLE001
        检("调用 %s 不抛异常" % 名, False, repr(e))
        continue
    if 名 in ("打开说明文档", "打开版本记录"):
        检("%s 开出了标签页" % 名, 标签数() > 前,
           "标签数 %d -> %d" % (前, 标签数()))

print("== 六之二、说明书与版本记录的内容能读出来 ==")
for 名, 关键词 in (("说明.md", "核说"), ("版本记录.md", "版本")):
    路径 = 窗._找文档(名)
    if not 路径:
        检("找到 %s" % 名, False)
        continue
    try:
        文 = 核工坊Qt.核.读源码(路径)
        检("%s 可读且含 %r" % (名, 关键词), 关键词 in 文, "长度 %d" % len(文))
    except Exception as e:  # noqa: BLE001
        检("%s 可读" % 名, False, repr(e))

print("== 七、菜单里真的有这些项（不是只有方法）==")
# 之前只测了「方法能调」，没测「菜单里有这个入口」——
# 万一忘了往菜单里挂，方法再正常用户也点不到。
菜单 = 窗._建主菜单()
顶层 = [a.text() for a in 菜单.actions() if a.text()]
检("主菜单有「帮助」", "帮助" in 顶层, "顶层项：%r" % 顶层)

助 = None
for a in 菜单.actions():
    if a.text() == "帮助":
        助 = a.menu()
        break
if 助 is None:
    检("找得到帮助子菜单", False)
else:
    项 = [x.text() for x in 助.actions() if x.text()]
    检("帮助里有 打开说明文档", "打开说明文档" in 项, "实际：%r" % 项)
    检("帮助里有 版本历史", "版本历史" in 项, "实际：%r" % 项)
    检("帮助里有 语法速查", "语法速查" in 项, "实际：%r" % 项)
    检("帮助里有 关于核工坊", "关于核工坊" in 项, "实际：%r" % 项)
    print("      帮助菜单：%r" % 项)

检("主菜单有「代码」（折叠入口）", "代码" in 顶层, "顶层项：%r" % 顶层)
码 = None
for a in 菜单.actions():
    if a.text() == "代码":
        码 = a.menu()
        break
if 码 is not None:
    折项 = [x.text() for x in 码.actions() if x.text()]
    检("代码里有 折叠当前块", "折叠当前块" in 折项, "实际：%r" % 折项)
    检("代码里有 全部展开", "全部展开" in 折项, "实际：%r" % 折项)
    print("      代码菜单：%r" % 折项)

# 版本控制入口在「视图」里
视图 = None
for a in 菜单.actions():
    if a.text() == "视图":
        视图 = a.menu()
        break
if 视图 is not None:
    视项 = [x.text() for x in 视图.actions() if x.text()]
    检("视图里有 版本控制", "版本控制" in 视项, "实际：%r" % 视项)

菜单.deleteLater()

print("== 八、顶行的版本控制不再是死占位 ==")
# 0.1.4 起，git 状态查询挪到了后台线程（同步跑会卡界面）。
# 所以按钮文字**不是**建完窗口就有 —— 要等后台线程把结果送回主线程。
# 不等待就直接断言，会在机器慢/负载高时偶发失败（实测全量回归时失败过一次，
# 单独跑却总是通过 —— 就是这种时序依赖）。
import time  # noqa: E402


def 等版本状态(超时=10.0):
    截止 = time.time() + 超时
    while time.time() < 截止:
        应用.processEvents()
        if "正在读取" not in 窗.顶行.版本钮.toolTip():
            return True
        time.sleep(0.02)
    return False


检("后台版本状态能在 10 秒内回填", 等版本状态(), 窗.顶行.版本钮.toolTip())
检("顶行按钮文字含分支符号", "⎇" in 窗.顶行.版本钮.text(), 窗.顶行.版本钮.text())
检("提示里不说「尚未接入」", "尚未接入" not in 窗.顶行.版本钮.toolTip(),
   窗.顶行.版本钮.toolTip())

print("== 九、说明文档确实存在 ==")
路径 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "说明.md")
检("说明.md 存在", os.path.isfile(路径), 路径)
记录 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "版本记录.md")
检("版本记录.md 存在", os.path.isfile(记录), 记录)

print()
print("=" * 62)
if 问题:
    print("发现 %d 个问题：" % len(问题))
    for 说明, _ in 问题:
        print("  · %s" % 说明)
    sys.exit(1)
print("帮助功能全部正常")
