# -*- coding: utf-8 -*-
"""冒烟：真实启动主窗、打开例子、切主题、开各面板、运行一个程序，全程抓异常。"""
import os
import sys
import traceback

这里 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 这里)
sys.argv = [sys.argv[0]]
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import 核工坊Qt

错误 = []
原hook = sys.excepthook


def hook(t, v, tb):
    错误.append("".join(traceback.format_exception(t, v, tb)))
    原hook(t, v, tb)


sys.excepthook = hook

应用 = QApplication.instance() or QApplication(sys.argv)
窗 = 核工坊Qt.主窗()
窗.show()
应用.processEvents()

步骤 = []


def 做(名, 函数):
    try:
        函数()
        应用.processEvents()
        步骤.append((名, "OK"))
    except Exception as e:  # noqa: BLE001
        步骤.append((名, "异常: %s" % e))
        错误.append(traceback.format_exc())


做("打开例子", lambda: 窗.打开(os.path.join(这里, "例子", "01_你好.xht")))
做("切浅色", lambda: 窗.换主题("浅色"))
做("切深色", lambda: 窗.换主题("深色"))
做("切字号", lambda: 窗.改字号(1))
做("切回字号", lambda: 窗.改字号(-1))
做("关行号", lambda: 窗.设行号(False))
做("开行号", lambda: 窗.设行号(True))
做("关缩进线", lambda: 窗.设缩进线(False))
做("开缩进线", lambda: 窗.设缩进线(True))
做("关高亮", lambda: 窗.设自动高亮(False))
做("开高亮", lambda: 窗.设自动高亮(True))
做("改制表2", lambda: 窗.设制表宽(2))
做("改制表4", lambda: 窗.设制表宽(4))
做("切项目栏", 窗.切换项目栏)
做("切项目栏回", 窗.切换项目栏)
做("切对照表", 窗.切换对照表)
做("切对照表回", 窗.切换对照表)
做("切运行窗", 窗.切换运行窗)
做("切运行窗回", 窗.切换运行窗)
做("新增标签", 窗.新建)
做("关闭标签", 窗.关闭当前)
做("存入配置", 窗.存配置)
做("重新载入项目树", lambda: 窗.装载项目树(窗.项目目录))

# 运行一个真程序
做("保存", lambda: 窗.保存(窗.当前, 弹窗=False))
做("运行", 窗.运行)

结束 = {"done": False}


def 收():
    窗.停止(静默=True)
    结束["done"] = True
    应用.quit()


QTimer.singleShot(4000, 收)
应用.exec()

print("=== 步骤 ===")
for 名, 状 in 步骤:
    print("  %-14s %s" % (名, 状))

出错 = [s for s in 步骤 if s[1] != "OK"]
print("\n=== 结果 ===")
if 出错 or 错误:
    print("有 %d 处问题" % (len(出错) + len(错误)))
    for e in 错误[:5]:
        print(e)
    sys.exit(1)
print("冒烟全部通过（%d 步）" % len(步骤))
sys.exit(0)
