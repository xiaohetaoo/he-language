# -*- coding: utf-8 -*-
"""把核工坊 Qt 版打包成 Windows exe。

与 tkinter 版打包（测试/打包.py）并存，互不影响，便于回退。

用法：
    python 测试/打包Qt.py              单文件（推荐分发）
    python 测试/打包Qt.py --目录        文件夹形式（启动快）
    python 测试/打包Qt.py --控制台      保留控制台窗口（排查问题用）

产物：dist/核工坊Qt.exe

注意：
  · PySide6 体积大，exe 约 65-80 MB，属正常
  · 必须带 --collect-all PySide6，否则 Qt 插件（平台/样式）缺文件
  · 打包后会自动让 exe 跑一次 --自检界面，验证资源完整
"""

import os
import shutil
import subprocess
import sys

这里 = os.path.dirname(os.path.abspath(__file__))
根目录 = os.path.dirname(这里)
产物名 = "核工坊Qt"


def 找解释器():
    return sys.executable or "python"


def 确保图标():
    素材 = os.path.join(根目录, "素材")
    需要 = ["核图标_%d.png" % n for n in (16, 24, 32, 48, 64, 128, 256)]
    缺 = [n for n in 需要 if not os.path.exists(os.path.join(素材, n))]
    if not 缺:
        return True
    生成 = os.path.join(根目录, "测试", "生成图标.py")
    if not os.path.exists(生成):
        print("缺少图标：%s" % "、".join(缺))
        return False
    print("图标不全，正在生成…")
    return subprocess.run([找解释器(), 生成], cwd=根目录).returncode == 0


def 主():
    参数 = sys.argv[1:]
    单文件 = "--目录" not in 参数
    控制台 = "--控制台" in 参数

    if not 确保图标():
        return 1

    # Qt 版入口：一个极小的启动文件，把参数转给 核工坊Qt
    入口 = os.path.join(根目录, "_启动Qt.py")
    with open(入口, "w", encoding="utf-8", newline="\n") as f:
        f.write(
            "# -*- coding: utf-8 -*-\n"
            '"""Qt 版打包入口。"""\n'
            "import os\nimport sys\n\n"
            "这里 = os.path.dirname(os.path.abspath(__file__))\n"
            "if 这里 not in sys.path:\n    sys.path.insert(0, 这里)\n\n"
            "def 主():\n"
            "    基 = getattr(sys, '_MEIPASS', 这里)\n"
            "    for 子 in ('', '素材'):\n"
            "        目录 = os.path.join(基, 子) if 子 else 基\n"
            "        if os.path.isdir(目录) and 目录 not in sys.path:\n"
            "            sys.path.insert(0, 目录)\n"
            "    参数 = sys.argv[1:]\n"
            "    if 参数 and 参数[0] == '--自检界面':\n"
            "        目录 = 参数[1] if len(参数) > 1 else '.'\n"
            "        return _自检(目录)\n"
            "    import 核工坊Qt\n"
            "    return 核工坊Qt.启动()\n\n"
            "def _自检(输出目录):\n"
            "    import json, time\n"
            "    from PySide6.QtWidgets import QApplication\n"
            "    import 核工坊Qt, 核\n"
            "    基 = getattr(sys, '_MEIPASS', 这里)\n"
            "    os.makedirs(输出目录, exist_ok=True)\n"
            "    应用 = QApplication([])\n"
            "    窗 = 核工坊Qt.主窗()\n"
            "    窗.show()\n"
            "    import time as _t\n"
            "    截止 = _t.time() + 3.0\n"
            "    while _t.time() < 截止:\n"
            "        应用.processEvents()\n"
            "        _t.sleep(0.02)\n"
            "    报告 = {\n"
            "        '运行方式': 'Qt 打包 exe',\n"
            "        '界面版本': 核.版本,\n"
            "        '顶行': 窗.顶行.项目名.text(),\n"
            "        '竖条按钮': list(窗.竖条.钮们),\n"
            "        '标签数': 窗.标签栏.count(),\n"
            "        '图标存在': os.path.exists(os.path.join(基, '素材', '核图标.ico')),\n"
            "        '对照表行数': len(窗.对照.toPlainText().splitlines()),\n"
            "    }\n"
            "    try:\n"
            "        窗.grab().save(os.path.join(输出目录, '自检_Qt.png'))\n"
            "    except Exception as e:\n"
            "        报告['截图失败'] = str(e)\n"
            "    with open(os.path.join(输出目录, '自检报告.json'), 'w', encoding='utf-8') as f:\n"
            "        json.dump(报告, f, ensure_ascii=False, indent=2)\n"
            "    print(json.dumps(报告, ensure_ascii=False, indent=2))\n"
            "    应用.quit()\n"
            "    return 0\n\n"
            "if __name__ == '__main__':\n"
            "    sys.exit(主())\n"
        )

    命令 = [
        找解释器(),
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile" if 单文件 else "--onedir",
        "--windowed" if not 控制台 else "--console",
        "--name",
        产物名,
        "--icon",
        os.path.join(根目录, "素材", "核图标.ico"),
        # PySide6 必须整包收集，否则缺 Qt 平台插件，运行时报 "could not find platform"
        "--collect-all",
        "PySide6",
        "--exclude-module",
        "tkinter",
    ]

    for 模块 in (
        "核工坊Qt", "编辑器", "主题", "设置窗口Qt", "查找对话框", "配置", "快速打开",
        "拖放", "圆角",
    ):
        命令 += ["--hidden-import", 模块]

    for 资源, 目标 in (
        ("素材", "素材"),
        ("例子", "例子"),
        ("核.py", "."),
        ("核工坊Qt.py", "."),
        ("编辑器.py", "."),
        ("主题.py", "."),
        ("设置窗口Qt.py", "."),
        ("查找对话框.py", "."),
        ("配置.py", "."),
        ("快速打开.py", "."),
        ("版本记录.md", "."),
        ("对照表.md", "."),
        ("说明.md", "."),
    ):
        源 = os.path.join(根目录, 资源)
        if not os.path.exists(源):
            print("缺少资源：%s" % 源)
            return 1
        命令 += ["--add-data", "%s;%s" % (源, 目标)]

    命令.append(入口)

    print("执行：\n  " + " \\\n  ".join(命令))
    结果 = subprocess.run(命令, cwd=根目录)
    if 结果.returncode != 0:
        print("打包失败，返回码 %s" % 结果.returncode)
        return 结果.returncode

    产物 = os.path.join(根目录, "dist", 产物名 + ".exe")
    if not os.path.exists(产物):
        print("没找到 %s" % 产物)
        return 1

    大小 = os.path.getsize(产物) / 1024.0 / 1024.0
    print("\n打包完成：%s（%.1f MB）" % (产物, 大小))
    return 校验产物(产物, 根目录)


def 校验产物(产物, 根目录):
    """让 exe 自己跑一次界面自检，确认 Qt 插件与资源都在。"""
    输出目录 = os.path.join(根目录, "dist", "打包自检")
    shutil.rmtree(输出目录, ignore_errors=True)
    print("\n正在让 exe 自检…")
    try:
        结果 = subprocess.run(
            [产物, "--自检界面", 输出目录],
            cwd=os.path.dirname(产物),
            capture_output=True,
            timeout=300,
        )
    except Exception as e:  # noqa: BLE001
        print("自检没能运行：%s" % e)
        return 1

    报告路径 = os.path.join(输出目录, "自检报告.json")
    if not os.path.exists(报告路径):
        print("自检失败：没生成报告")
        print((结果.stdout or b"").decode("utf-8", "replace")[-800:])
        print((结果.stderr or b"").decode("utf-8", "replace")[-800:])
        return 1

    import json

    with open(报告路径, encoding="utf-8") as f:
        报告 = json.load(f)

    问题 = []
    if not 报告.get("图标存在"):
        报告 and 问题.append("素材/核图标.ico 没打进 exe")
    if 报告.get("标签数", 0) < 1:
        问题.append("标签页建不起来")
    if 报告.get("对照表行数", 0) < 10:
        问题.append("对照表没填充")
    if not 报告.get("竖条按钮"):
        问题.append("左侧竖条按钮缺失")

    print("自检结果：")
    for 键 in ("运行方式", "界面版本", "顶行", "标签数", "对照表行数", "图标存在"):
        print("  %-10s %s" % (键, 报告.get(键)))

    if 问题:
        print("\n自检不通过：")
        for 项 in 问题:
            print("  × %s" % 项)
        return 1
    print("\n自检通过，资源完整。")
    return 0


if __name__ == "__main__":
    sys.exit(主())
