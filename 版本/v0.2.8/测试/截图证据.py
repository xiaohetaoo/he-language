# -*- coding: utf-8 -*-
"""在**真实 Windows 平台**（非 offscreen）截取界面证据。

用法：
    py -3 测试/截图证据.py [输出目录]

不传输出目录时，默认写到系统临时目录下的 核工坊截图_<时间戳>/，
**不会往仓库里塞图片**（P3-4）。要留档就显式传一个目录。

注意：
  · 根目录按本文件位置推算，不再硬编码 D:\\dsh\\dsh5 ——
    仓库复制到任何路径都能跑。
  · 配置目录**强制**指向临时目录：以前用 setdefault，环境里已经有
    核工坊_配置目录 时就不覆盖，脚本会去改用户真实的 工坊配置.json
    （里面存着用户的字号、主题、最近打开）。现在一律用临时目录，
    结束后删掉。
"""
import os
import shutil
import sys
import tempfile
import time

根目录 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if 根目录 not in sys.path:
    sys.path.insert(0, 根目录)

if len(sys.argv) > 1:
    输出 = os.path.abspath(sys.argv[1])
else:
    输出 = os.path.join(tempfile.gettempdir(),
                        "核工坊截图_" + time.strftime("%Y%m%d-%H%M%S"))
os.makedirs(输出, exist_ok=True)

# **强制**隔离配置：不用 setdefault，环境里有值也覆盖掉。
临时配置 = tempfile.mkdtemp(prefix="核工坊截图配置_")
os.environ["核工坊_配置目录"] = 临时配置

from PySide6.QtCore import Qt, QTimer  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QApplication, QCheckBox, QDialog, QHBoxLayout, QVBoxLayout,
)

import 核工坊Qt as m  # noqa: E402
import 帮助窗口  # noqa: E402

应用 = QApplication(sys.argv)


def 等(毫秒=250):
    """真的跑事件循环等一会儿 —— 截图前必须让 Qt 完成排版与重绘。"""
    起 = time.time()
    while time.time() - 起 < 毫秒 / 1000.0:
        应用.processEvents()
        time.sleep(0.01)


def 存(部件, 名):
    等(300)
    图 = 部件.grab()
    路 = os.path.join(输出, 名 + ".png")
    图.save(路)
    print("  %-34s %dx%d" % (名 + ".png", 图.width(), 图.height()))
    return 路


窗 = m.主窗()
窗.resize(1180, 760)
窗.show()
等(500)

样例 = os.path.join(根目录, "例子", "01_你好.xht")
窗.打开(样例)
等(300)
窗.新建()
窗.当前.置文本(
    "核定义 求和(甲, 乙)：\n"
    "    核若 甲 > 乙：\n"
    "        核返回 甲 + 乙\n"
    "    核否则：\n"
    "        核返回 乙\n"
    "\n"
    '核说("求和结果：", 求和(3, 4))\n',
    标记已改=True)
窗.装载项目树(根目录)
等(400)

记录 = []
for 主题名 in ("深色", "浅色"):
    窗.换主题(主题名)
    等(400)
    for 字号, 标签 in ((12, "12"), (40, "40")):
        # 设字号() 收的是**绝对值**（改字号() 才收增量）。
        # 一开始这里传了差值，于是所有截图其实是 8 号和 32 号拍的。
        窗.设字号(字号)
        等(500)
        前 = "%s_%s号" % (主题名, 标签)
        记录.append(存(窗, "主窗_" + 前))

        # 编辑区单独截（含行号栏、折叠三角、当前行）
        编 = 窗.当前
        记录.append(存(编, "编辑区_" + 前))

        # 设置窗口
        try:
            设置 = m.设置窗口Qt.设置对话框(窗)
        except AttributeError:
            import 设置窗口Qt
            设置 = 设置窗口Qt.设置对话框(窗)
        设置.show()
        等(400)
        记录.append(存(设置, "设置_" + 前))
        设置.取消()
        等(200)

        # 查找对话框
        import 查找对话框
        查 = 查找对话框.查找对话框(窗, 编)
        查.show()
        等(300)
        记录.append(存(查, "查找_" + 前))
        查.close()
        等(150)

        # 版本历史 / 关于
        历 = 帮助窗口.版本历史对话框(窗, 核.版本, 根目录)
        历.show()
        等(300)
        记录.append(存(历, "版本历史_" + 前))
        历.close()

        关 = 帮助窗口.关于对话框(窗, 核.版本)
        关.show()
        等(300)
        记录.append(存(关, "关于_" + 前))
        关.close()
        等(150)

        # 快速打开
        import 快速打开
        快 = 快速打开.快速打开(窗)
        快.show()
        等(300)
        快.输入框.setText("xht")
        等(300)
        记录.append(存(快, "快速打开_" + 前))
        快.close()
        等(150)

        # 复选框三态（同一张图里排三行）
        盒 = QDialog(窗)
        盒.setWindowTitle("复选框三态")
        盒.setStyleSheet(窗.styleSheet())
        排 = QVBoxLayout(盒)
        行们 = []
        for 文本, 态 in (("未选中", "off"), ("已选中", "on"),
                         ("半选（部分）", "part"), ("已禁用", "dis")):
            行 = QHBoxLayout()
            勾 = QCheckBox(文本)
            if 态 == "on":
                勾.setChecked(True)
            elif 态 == "part":
                勾.setTristate(True)
                勾.setCheckState(Qt.PartiallyChecked)
            elif 态 == "dis":
                勾.setEnabled(False)
            行.addWidget(勾)
            行.addStretch(1)
            排.addLayout(行)
            行们.append(勾)
        盒.resize(320, 200)
        盒.show()
        等(400)
        记录.append(存(盒, "复选框_" + 前))
        盒.close()

# 40 号字时控制台是否还保持 13px 固定（P2-24 的核心证据）
窗.设字号(40)
窗.换主题("深色")
等(500)
窗.切换运行窗()
等(300)
窗._写控制台(">>> 编辑器 40 号字时，控制台仍是固定 13px\n")
窗._写控制台("    如果字号跟着编辑器变大，说明固定字号规则没生效\n")
记录.append(存(窗.控制台, "控制台固定字号_深色_40号"))
窗.设字号(12)
窗.换主题("深色")
等(500)
窗._写控制台(">>> 编辑器 12 号字时，控制台同样是 13px\n")
记录.append(存(窗.控制台, "控制台固定字号_深色_12号"))
窗.切换运行窗()

窗.设字号(12)
窗.换主题("深色")
等(300)

print()
print("共 %d 张，全部在 %s" % (len(记录), 输出))
窗.停止(静默=True)
窗.close()
# 临时配置用完就删：里面只有这个脚本自己写出来的设置，
# 留着只会在 %TEMP% 里越堆越多（P3-4）。
shutil.rmtree(临时配置, ignore_errors=True)
