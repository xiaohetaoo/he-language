# -*- coding: utf-8 -*-
"""一键跑完全部回归测试。

打包前会自动调用它（见 测试/打包Qt.py）。任何一项不过就返回 1，
避免把有问题的版本打成 exe 发出去。

用法：python 测试/跑全部.py
"""

import os
import subprocess
import sys
import tempfile

根目录 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

测试集 = [
    ("内核自测", "自测.py"),
    ("对照表自检", "自检对照表.py"),
    ("Qt 功能自测", "自测Qt.py"),
    ("逐项验证（菜单/对话框/运行）", "逐项验证Qt.py"),
    ("输入自测（吞字）", "输入自测.py"),
    ("界面可见性审查", "审查可见性.py"),
    ("冒烟（真实运行程序）", "冒烟Qt.py"),
    ("窗口缩放与边缘判定", "查缩放.py"),
    # —— 以下为 0.0.11 代码审查新增 ——
    ("高亮与翻译一致性", "查高亮一致.py"),
    ("自动配对括号行为", "查配对.py"),
    ("切换注释行为", "查注释切换.py"),
    ("菜单动作不泄漏", "查菜单泄漏.py"),
]


def 主():
    print("=" * 62)
    print("核工坊 · 全量回归测试")
    print("=" * 62)
    环境 = dict(os.environ)
    环境["PYTHONIOENCODING"] = "utf-8"
    # 把配置目录指到临时目录：测试会改界面设置并写盘，若直接写到项目里，
    # 跑一次回归就把用户真实的字号/制表宽/行号开关覆盖掉了
    # （曾经把制表宽写成 2，导致下一次自测按「应为 4」失败）。
    临时配置 = tempfile.mkdtemp(prefix="核工坊回归配置_")
    环境["核工坊_配置目录"] = 临时配置
    失败项 = []
    for 名称, 脚本 in 测试集:
        路径 = os.path.join(根目录, "测试", 脚本)
        if not os.path.exists(路径):
            print("\n--- %s：跳过（找不到 %s）" % (名称, 脚本))
            continue
        print("\n--- %s（%s）" % (名称, 脚本))
        # 每个测试集用独立的配置目录，避免上一项改的设置影响下一项
        环境["核工坊_配置目录"] = tempfile.mkdtemp(prefix="核工坊回归_")
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
