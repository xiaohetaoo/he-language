# -*- coding: utf-8 -*-
"""归档当前版本。

把内核、界面、模块与示例快照到 `版本/v0.0.1/`，并更新版本记录。
每次发布新版本时跑一次：

    python 测试/归档版本.py            核核 归档当前版本
    python 测试/归档版本.py --列表     核核 查看已归档版本

归档内容：
    版本/v0.0.1/核.py、核工坊.py、拖放.py、圆角.py、启动器.py
    版本/v0.0.1/例子/、素材/
    版本/v0.0.1/版本信息.txt
"""

import datetime
import os
import shutil
import sys

这里 = os.path.dirname(os.path.abspath(__file__))
根目录 = os.path.dirname(这里)
sys.path.insert(0, 根目录)

import 核  # noqa: E402

版本根 = os.path.join(根目录, "版本")

代码文件 = (
    "核.py", "核工坊.py", "设置窗口.py", "拖放.py", "圆角.py", "启动器.py",
    # Qt 版界面（0.0.6 起并行存在，tkinter 版保留可回退）
    "主题.py", "编辑器.py", "核工坊Qt.py", "设置窗口Qt.py", "查找对话框.py",
    "快速打开.py", "配置.py",
    # Qt 版打包入口（PyInstaller 用的就是它，别漏）
    "_启动Qt.py",
    # 0.0.12 起：帮助、版本控制
    "帮助窗口.py", "版本控制.py", "版本控制窗口.py",
)
资源目录 = ("例子", "素材")
#: 一起快照的文档。README 和 LICENSE 也要 —— 归档的目的是「这一版什么样」
#: 都能回看，缺了许可证声明就不完整。
文档文件 = ("说明.md", "版本记录.md", "README.md", "LICENSE", "对照表.md")


def 归档(覆盖=False):
    版本 = 核.版本
    目标 = os.path.join(版本根, "v%s" % 版本)
    if os.path.exists(目标):
        if not 覆盖:
            print("版本 v%s 已存在：%s" % (版本, 目标))
            print("如需重新归档（例如同一版本号内还在修 bug），加 --覆盖。")
            return 1
        # 覆盖前把旧的挪到 _旧_ 备份，避免手滑丢掉上一版内容
        备份 = os.path.join(版本根, "_旧_v%s" % 版本)
        shutil.rmtree(备份, ignore_errors=True)
        try:
            os.rename(目标, 备份)
            print("已把原 v%s 备份到 %s" % (版本, os.path.basename(备份)))
        except OSError as e:
            print("无法备份旧版本（%s），已中止，未做改动。" % e)
            return 1

    os.makedirs(目标, exist_ok=True)
    复制 = []
    for 名 in 代码文件:
        源 = os.path.join(根目录, 名)
        if os.path.exists(源):
            shutil.copy2(源, os.path.join(目标, 名))
            复制.append(名)
    for 名 in 资源目录:
        源 = os.path.join(根目录, 名)
        if os.path.isdir(源):
            shutil.copytree(源, os.path.join(目标, 名))
            复制.append(名 + "/")
    for 名 in 文档文件:
        源 = os.path.join(根目录, 名)
        if os.path.exists(源):
            shutil.copy2(源, os.path.join(目标, 名))
            复制.append(名)

    时间 = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(os.path.join(目标, "版本信息.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("核语言 版本 v%s\n" % 版本)
        f.write("归档时间：%s\n" % 时间)
        f.write("源文件后缀：%s\n" % 核.扩展名)
        f.write("\n包含内容：\n")
        for 名 in 复制:
            f.write("  %s\n" % 名)

    print("已归档 v%s → %s" % (版本, 目标))
    print("  包含：%s" % "、".join(复制))
    print("\n记得在 版本记录.md 里补一句本版要点。")
    return 0


def 列表():
    if not os.path.isdir(版本根):
        print("还没有任何归档版本。")
        return 0
    版本们 = sorted(
        (d for d in os.listdir(版本根) if d.startswith("v")),
        key=lambda s: [int(x) for x in s[1:].split(".") if x.isdigit()],
    )
    if not 版本们:
        print("还没有任何归档版本。")
        return 0
    print("已归档 %d 个版本：\n" % len(版本们))
    for d in 版本们:
        路径 = os.path.join(版本根, d)
        信息 = os.path.join(路径, "版本信息.txt")
        时间 = ""
        if os.path.exists(信息):
            with open(信息, encoding="utf-8") as f:
                for 行 in f:
                    if 行.startswith("归档时间："):
                        时间 = 行.strip().split("：", 1)[1]
                        break
        文件数 = sum(len(fs) for _, _, fs in os.walk(路径))
        print("  %-8s %-20s %d 个文件" % (d, 时间, 文件数))
    return 0


if __name__ == "__main__":
    if "--列表" in sys.argv:
        sys.exit(列表())
    sys.exit(归档(覆盖="--覆盖" in sys.argv))
