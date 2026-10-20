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

    for 资源 in ("素材", "例子", "核.py", "核工坊.py", "说明.md"):
        源 = os.path.join(根目录, 资源)
        if not os.path.exists(源):
            print("缺少资源：%s" % 源)
            return 1
        命令 += ["--add-data", "%s;%s" % (源, os.path.dirname(资源) or ".")]

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
    else:
        print("\n打包完成，但没找到 dist/核工坊.exe，请检查输出。")
    return 0


if __name__ == "__main__":
    sys.exit(主())
