# -*- coding: utf-8 -*-
"""一键跑完全部回归测试。

打包前会自动调用它（见 测试/打包Qt.py）。任何一项不过就返回 1，
避免把有问题的版本打成 exe 发出去。

用法：python 测试/跑全部.py
"""

import os
import subprocess
import sys

根目录 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

测试集 = [
    ("内核自测", "自测.py"),
    ("对照表自检", "自检对照表.py"),
    ("Qt 功能自测", "自测Qt.py"),
    ("输入自测（吞字）", "输入自测.py"),
    ("界面可见性审查", "审查可见性.py"),
]


def 主():
    print("=" * 62)
    print("核工坊 · 全量回归测试")
    print("=" * 62)
    环境 = dict(os.environ)
    环境["PYTHONIOENCODING"] = "utf-8"
    失败项 = []
    for 名称, 脚本 in 测试集:
        路径 = os.path.join(根目录, "测试", 脚本)
        if not os.path.exists(路径):
            print("\n--- %s：跳过（找不到 %s）" % (名称, 脚本))
            continue
        print("\n--- %s（%s）" % (名称, 脚本))
        结果 = subprocess.run(
            [sys.executable, 路径], cwd=根目录, env=环境, capture_output=True
        )
        输出 = (结果.stdout or b"").decode("utf-8", "replace")
        错误 = (结果.stderr or b"").decode("utf-8", "replace")
        # unittest 把结果写在 stderr，所以两边都要看
        合并 = (输出 + "\n" + 错误).strip()
        # 只打印尾部若干行，前面太长的细节没必要刷屏
        行 = [行 for 行 in 合并.splitlines() if 行.strip()]
        for 行 in 行[-14:]:
            print("  " + 行)
        if 结果.returncode != 0:
            失败项.append(名称)

    print("\n" + "=" * 62)
    if 失败项:
        print("回归失败 %d 项：%s" % (len(失败项), "、".join(失败项)))
        return 1
    print("全量回归通过（%d 项测试集）" % len(测试集))
    return 0


if __name__ == "__main__":
    sys.exit(主())
