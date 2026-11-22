# -*- coding: utf-8 -*-
"""真实 Windows 平台（非 offscreen）截取本轮视觉证据并记录实测数值。

用法：py -3 测试\截图专项.py <输出目录>
"""
import json
import os
import sys
import tempfile

根目录 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, 根目录)

输出 = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(
    tempfile.gettempdir(), "专项截图")
os.makedirs(输出, exist_ok=True)
临时配置 = tempfile.mkdtemp(prefix="专项配置_")
os.environ["核工坊_配置目录"] = 临时配置

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QApplication, QCheckBox, QDialog, QHBoxLayout, QLabel, QStyle, QVBoxLayout,
)

import 核工坊Qt as m  # noqa: E402
import 帮助窗口  # noqa: E402
import 版本控制窗口  # noqa: E402

应用 = QApplication(sys.argv)
记录 = {}


def 等(毫秒=260):
    起 = __import__("time").time()
    while (__import__("time").time() - 起) * 1000 < 毫秒:
        应用.processEvents()
        应用.processEvents()


def 存(件, 名):
    应用.processEvents()
    等(200)
    图 = 件.grab()
    路径 = os.path.join(输出, 名 + ".png")
    图.save(路径)
    print("  %-34s %dx%d" % (名 + ".png", 图.width(), 图.height()))
    return 路径


窗 = m.主窗()
窗.resize(1180, 760)
窗.show()
等(500)

# 关于页（P3-1）
关 = 帮助窗口.关于对话框(窗, 核.版本)
关.show()
等()
存(关, "关于页_版本行")
关.close()

for 字号 in (12, 40):
    for 主题名 in ("深色", "浅色"):
        窗.换主题(主题名)
        窗.设字号(字号)
        等(360)
        后 = "%s_%d号" % (主题名, 字号)

        # 版本控制面板（P1-5：diffView 必须固定 13px）
        面 = 版本控制窗口.版本控制窗口(窗, 根目录)
        面.resize(620, 720)
        面.show()
        等(360)
        存(面, "版本面板_" + 后)
        值 = {
            "diffView_height": 面.差异.fontMetrics().height(),
            "diffView_字号px": 面.差异.font().pixelSize(),
            "文件列表_height": 面.树.fontMetrics().height(),
            "编辑区_height": 窗.当前.fontMetrics().height() if 窗.当前 else 0,
        }
        记录[后] = 值
        面.close()
        等(120)

        # 设置页里的真实复选框（P2-2 的验收位置）
        路 = None
        try:
            import 设置窗口Qt  # noqa: E402

            设 = 设置窗口Qt.设置对话框(窗)
            设.show()
            等(360)
            存(设, "设置页_" + 后)
            _勾们 = 设.findChildren(QCheckBox)
            if _勾们:
                记录[后]["设置页勾"] = [
                    _勾们[0].sizeHint().width(), _勾们[0].sizeHint().height()]
                记录[后]["设置页指示器"] = _勾们[0].style().pixelMetric(
                    QStyle.PM_IndicatorHeight, None, _勾们[0])
            设.取消()
            等(120)
        except Exception as e:  # noqa: BLE001
            print("  设置页截图跳过：%s" % e)

        # 设置页复选框（P2-2：固定 14px）
        框 = QDialog()
        框.setStyleSheet(窗.styleSheet())
        框.setWindowTitle("复选框专项")
        纵 = QVBoxLayout(框)
        纵.setContentsMargins(18, 16, 18, 16)
        纵.setSpacing(10)
        词 = QLabel("复选框指示器尺寸（固定，不随编辑器字号）")
        纵.addWidget(词)
        横向 = QHBoxLayout()
        组 = []
        for 文 in ("未选中", "已选中", "半选", "已禁用"):
            勾 = QCheckBox(文)
            勾.show()
            if 文 == "已选中":
                勾.setChecked(True)
            elif 文 == "半选":
                勾.setTristate(True)
                勾.setCheckState(Qt.PartiallyChecked)
            elif 文 == "已禁用":
                勾.setEnabled(False)
            横向.addWidget(勾)
            组.append(勾)
        纵.addLayout(横向)
        框.resize(460, 120)
        框.show()
        等(320)
        存(框, "复选框_" + 后)
        记录[后].update({
            "勾_sizeHint": [组[0].sizeHint().width(), 组[0].sizeHint().height()],
            "指示器": 组[0].style().pixelMetric(QStyle.PM_IndicatorHeight, None, 组[0]),
        })
        框.close()
        等(100)

窗.设字号(12)
窗.换主题("深色")
窗.close()

print()
print(json.dumps(记录, ensure_ascii=False, indent=2))
print()
a, b = 记录["深色_12号"], 记录["深色_40号"]
print("diffView：12 号 %dpx / 40 号 %dpx  → %s"
      % (a["diffView_height"], b["diffView_height"],
         "固定" if a["diffView_height"] == b["diffView_height"] else "会变！"))
print("编辑区：  12 号 %dpx / 40 号 %dpx"
      % (a["编辑区_height"], b["编辑区_height"]))
print("复选框：  12 号 %r / 40 号 %r  → %s"
      % (a["勾_sizeHint"], b["勾_sizeHint"],
         "固定" if a["勾_sizeHint"] == b["勾_sizeHint"] else "会变！"))

import shutil  # noqa: E402
shutil.rmtree(临时配置, ignore_errors=True)
