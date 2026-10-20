# -*- coding: utf-8 -*-
"""把核工坊打包成 Windows exe。

用法：
    python 测试/打包.py              默认单文件（推荐分发）
    python 测试/打包.py --目录        保留文件夹形式（启动快）
    python 测试/打包.py --控制台      保留控制台窗口（排查问题用）

产物在 dist/ 下。依赖 PyInstaller：
    pip install -i https://pypi.tuna.tsinghua.edu.cn/simple pyinstaller
"""

import os
import shutil
import subprocess
import sys

这里 = os.path.dirname(os.path.abspath(__file__))
根目录 = os.path.dirname(这里)


def 找解释器():
    return sys.executable or "python"


def 确保图标(根目录):
    """打包前确保素材里有各尺寸 PNG（设窗口图标要用），缺了就现生成。"""
    素材 = os.path.join(根目录, "素材")
    需要 = ["核图标_%d.png" % n for n in (16, 24, 32, 48, 64, 128, 256)]
    缺 = [n for n in 需要 if not os.path.exists(os.path.join(素材, n))]
    if not 缺:
        return True
    生成 = os.path.join(根目录, "测试", "生成图标.py")
    if not os.path.exists(生成):
        print("缺少图标文件：%s" % "、".join(缺))
        return False
    print("图标不全（缺 %d 个），正在生成…" % len(缺))
    结果 = subprocess.run([找解释器(), 生成], cwd=根目录)
    return 结果.returncode == 0


def 主():
    参数 = sys.argv[1:]
    单文件 = "--目录" not in 参数
    控制台 = "--控制台" in 参数
    确保图标(根目录)

    命令 = [
        找解释器(),
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile" if 单文件 else "--onedir",
        "--windowed" if not 控制台 else "--console",
        "--name",
        "核工坊",
        "--icon",
        os.path.join(根目录, "素材", "核图标.ico"),
    ]
    # 代码模块走 --hidden-import，其余附件走 --add-data
    for 模块 in ("拖放", "圆角", "设置窗口"):
        命令 += ["--hidden-import", 模块]

    # 每个资源要写清「源路径;打进 exe 里的目标目录」。
    # 注意：目标目录必须显式写出来。若用路径推导，对「素材」「例子」
    # 这类顶层目录会得到空串并退化成 "."，整个 素材/ 被摊到根目录，
    # exe 里便找不到 素材/核图标.png，图标与欢迎页会集体失效。
    for 资源, 目标 in (
        ("素材", "素材"),
        ("例子", "例子"),
        ("核.py", "."),
        ("核工坊.py", "."),
        ("设置窗口.py", "."),
        ("拖放.py", "."),
        ("圆角.py", "."),
        ("说明.md", "."),
    ):
        源 = os.path.join(根目录, 资源)
        if not os.path.exists(源):
            print("缺少资源：%s" % 源)
            return 1
        命令 += ["--add-data", "%s;%s" % (源, 目标)]

    命令.append(os.path.join(根目录, "启动器.py"))

    print("执行：\n  " + " \\\n  ".join(命令))
    结果 = subprocess.run(命令, cwd=根目录)
    if 结果.returncode != 0:
        print("打包失败，返回码 %s" % 结果.returncode)
        return 结果.returncode

    产物 = os.path.join(根目录, "dist", "核工坊.exe")
    if os.path.exists(产物):
        大小 = os.path.getsize(产物) / 1024.0 / 1024.0
        print("\n打包完成：%s（%.1f MB）" % (产物, 大小))
        print("这个 exe 自带内核，目标机器不需要安装 Python。")
        return 校验产物(产物, 根目录)
    print("\n打包完成，但没找到 dist/核工坊.exe，请检查输出。")
    return 0


def 校验产物(产物, 根目录):
    """让 exe 自己跑一次界面自检，确认资源真的打进去了。

    这一步是血泪教训：曾经因为 --add-data 的目标目录写成 "."，
    整个 素材/ 被摊平到根目录，exe 里找不到 素材/核图标.png，
    标题栏图标与欢迎页图标集体消失，而外部截图看起来「像是旧界面」。
    现在打包后立刻让 exe 自证，不通过就直接报错。
    """
    输出目录 = os.path.join(根目录, "dist", "打包自检")
    shutil.rmtree(输出目录, ignore_errors=True)
    print("\n正在让 exe 自检（验证资源是否完整）…")
    try:
        结果 = subprocess.run(
            [产物, "--自检界面", 输出目录],
            cwd=os.path.dirname(产物),
            capture_output=True,
            timeout=180,
        )
    except Exception as e:  # noqa: BLE001
        print("自检没能运行：%s" % e)
        return 1

    报告路径 = os.path.join(输出目录, "自检报告.json")
    if not os.path.exists(报告路径):
        print("自检失败：没有生成报告。")
        print((结果.stderr or b"").decode("utf-8", "replace")[-800:])
        return 1

    import json

    with open(报告路径, encoding="utf-8") as f:
        报告 = json.load(f)

    问题 = []
    if not 报告.get("图标PNG存在"):
        问题.append("素材/核图标.png 没打进 exe（--add-data 目标目录写错）")
    if not 报告.get("欢迎图"):
        问题.append("欢迎页图标加载失败：%s" % 报告.get("欢迎失败原因", "原因未知"))
    if 报告.get("工具栏") != ["运行", "停止", "保存", "打开", "设置"]:
        问题.append("工具栏不对：%s" % 报告.get("工具栏"))
    if 报告.get("左条") != ["项目", "对照表"]:
        问题.append("左条按钮不对：%s" % 报告.get("左条"))
    if not 报告.get("有设置对话框"):
        问题.append("设置对话框没打进去")
    项目目录 = str(报告.get("实际项目目录", ""))
    if os.path.basename(项目目录).lower() == "dist":
        问题.append("默认项目目录仍是 dist：%s" % 项目目录)

    print("自检结果：")
    for 键 in ("运行方式", "界面版本", "实际项目目录", "欢迎图", "图标PNG存在"):
        print("  %-12s %s" % (键, 报告.get(键)))

    if 问题:
        print("\n自检不通过：")
        for 项 in 问题:
            print("  × %s" % 项)
        return 1
    print("\n自检通过，资源完整。")
    return 0


if __name__ == "__main__":
    sys.exit(主())
