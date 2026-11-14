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


def 清理残留进程(名="核工坊Qt"):
    """打包前先杀掉还在跑的旧 exe。

    PyInstaller 要覆盖 dist 里那个 exe，若上一次打出来的程序还开着
    （或者运行用户程序时留下的孤儿进程还活着），文件就被锁住，
    构建会在链接/替换那一步失败，报一句很难懂的
    「Permission denied」。与其让用户去猜，不如打包前主动清掉。
    只杀同名进程，不会牵连其他程序。
    """
    if sys.platform != "win32":
        return
    try:
        r = subprocess.run(
            ["taskkill", "/F", "/IM", 名 + ".exe"],
            capture_output=True, timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
        )
    except (OSError, subprocess.SubprocessError):
        return
    # 返回码 128（找不到进程）是正常情况：本来就没在跑。
    if r.returncode == 0:
        print("已结束残留的 %s.exe" % 名)


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


def 跑回归():
    """打包前把全部测试跑一遍，不过就别打包。"""
    脚本 = os.path.join(根目录, "测试", "跑全部.py")
    if not os.path.exists(脚本):
        print("找不到回归测试脚本，跳过")
        return True
    print("\n先跑一遍全部回归测试…")
    环境 = dict(os.environ)
    环境["PYTHONIOENCODING"] = "utf-8"
    结果 = subprocess.run([找解释器(), 脚本], cwd=根目录, env=环境)
    return 结果.returncode == 0


def 主():
    参数 = sys.argv[1:]
    单文件 = "--目录" not in 参数
    控制台 = "--控制台" in 参数

    if not 确保图标():
        return 1

    if "--跳过测试" not in 参数 and not 跑回归():
        print("\n回归测试没过，已停止打包。")
        return 1

    # 先清掉还在跑的旧 exe：它锁着 dist 里的文件，覆盖会失败。
    清理残留进程()

    # Qt 版入口：_启动Qt.py 是仓库里**实际存在、被 git 跟踪**的文件，
    # 打包时不再用内嵌字符串模板重新生成它 —— 那是双事实源：
    # 模板和文件各自演化，改一边必漏另一边，而打包只认模板，
    # 于是「我明明改了入口，打出来的 exe 却没变」这类问题极难查。
    # 现在只用文件本身；缺了就直接报错，不偷偷生成一份。
    入口 = os.path.join(根目录, "_启动Qt.py")
    if not os.path.isfile(入口):
        print("缺少打包入口文件：%s" % 入口)
        return 1

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
        # 0.0.12 起：帮助、版本控制。这三个是运行时 import 的，
        # 静态分析扫不到，漏了 exe 里点「版本历史」就会报 ModuleNotFoundError。
        "帮助窗口", "版本控制", "版本控制窗口",
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
        ("帮助窗口.py", "."),
        ("版本控制.py", "."),
        ("版本控制窗口.py", "."),
        ("版本记录.md", "."),
        ("对照表.md", "."),
        ("说明.md", "."),
        ("LICENSE", "."),
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
    if not 报告.get("竖条图标齐全"):
        问题.append("竖条图标没画出来（pixmap 为空）")
    if 报告.get("顶行有设置"):
        问题.append("顶行重复出现了设置入口")
    # 字号必须真的生效：QSS 里 font-size 的优先级高于 setFont()，
    # 打包后若占位符没被替换成具体数值，改字号看不出任何变化。
    if "字号真的生效" in 报告 and not 报告["字号真的生效"]:
        问题.append(
            "字号不生效（10pt 行高 %s，20pt 行高 %s）"
            % (报告.get("字号行高_10pt"), 报告.get("字号行高_20pt"))
        )
    if "行号跟随字号" in 报告 and not 报告["行号跟随字号"]:
        问题.append("行号栏字号没跟随正文")
    # 0.0.12：帮助与版本控制是运行时 import 的，静态分析扫不到。
    # 打包时漏了 --hidden-import 的话，exe 里点帮助就会 ModuleNotFoundError。
    for 名 in ("帮助窗口", "版本控制", "版本控制窗口"):
        if 报告.get("模块_" + 名) is not True:
            问题.append("模块 %s 没能导入（%s）" % (名, 报告.get("模块_" + 名)))
    if 报告.get("打开说明文档") is not True:
        问题.append("打不开说明.md（%s）" % 报告.get("打开说明文档"))
    if 报告.get("折叠可用") is not True:
        问题.append("代码折叠不可用（%s）" % 报告.get("折叠可用"))
    elif 报告.get("折叠真的生效") is not True:
        问题.append("折叠没真的隐藏行")
    # 从 dist 里跑 exe 时项目目录会上移一级到仓库根，那里有 版本/ 和 .git。
    # 若这里读到 0 个归档或版本控制不可用，说明目录推断坏了。
    if 报告.get("读到归档版本数") == 0:
        问题.append("读不到任何归档版本（项目目录 %s）" % 报告.get("版本控制_探测目录"))
    elif isinstance(报告.get("读到归档版本数"), str):
        问题.append("读归档版本失败（%s）" % 报告.get("读到归档版本数"))

    print("自检结果：")
    for 键 in (
        "运行方式",
        "界面版本",
        "顶行",
        "竖条按钮",
        "竖条图标齐全",
        "顶行有设置",
        "标签数",
        "对照表行数",
        "图标存在",
        "启动字号",
        "字号真的生效",
        "行号跟随字号",
        "恢复后字号",
        "模块_帮助窗口",
        "模块_版本控制",
        "模块_版本控制窗口",
        "打开说明文档",
        "折叠可用",
        "折叠真的生效",
        "版本控制可用",
        "版本控制_探测目录",
        "读到归档版本数",
    ):
        print("  %-18s %s" % (键, 报告.get(键)))

    if 问题:
        print("\n自检不通过：")
        for 项 in 问题:
            print("  × %s" % 项)
        return 1
    print("\n自检通过，资源完整。")
    return 0


if __name__ == "__main__":
    sys.exit(主())
