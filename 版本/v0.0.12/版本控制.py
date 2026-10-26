# -*- coding: utf-8 -*-
"""git 版本控制接入（**只读**）。

范围说明 —— 这里刻意只做「看」，不做「改」：
    · 读分支名、改动文件、上游领先/落后几个提交
    · 让用户点一下就能打开某个改动过的文件
**不**实现提交、暂存、推送、拉取。

原因：这个项目对推送有硬约定（每次 push / 打 tag / 发 Release 都要先经
用户同意）。把提交按钮做进界面，等于给了一条绕过该约定的快捷路径 ——
一个手滑就可能把不该公开的东西推上去。要看改动、要提交，用真正的
git 客户端（或命令行）更稳妥。

git 不存在、目录不是仓库、git 命令超时，一律降级成「未启用」，
绝不让界面因为版本控制而报错或卡住。
"""

import os
import shutil
import subprocess
import sys

#: git 命令的超时（秒）。仓库很大时 status 也可能慢，给足但不无限等。
超时 = 6.0


def 找git():
    """找到可用的 git 可执行文件，找不到返回 None。"""
    路径 = shutil.which("git")
    if 路径:
        return 路径
    # 打包成 exe 后 PATH 可能不含 Git；再试几个常见安装位置
    for 候选 in (
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files (x86)\Git\cmd\git.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Git", "cmd", "git.exe"),
    ):
        if 候选 and os.path.isfile(候选):
            return 候选
    return None


def _无窗口标志():
    """Windows 上别弹出黑色控制台窗口。

    GUI 程序里调 subprocess 若不设这个标志，每次跑 git 都会闪一下 cmd 窗口，
    用户会以为程序在乱开窗口。
    """
    if sys.platform != "win32":
        return 0
    return getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)


def _跑(目录, 参数):
    """跑一条只读 git 命令，返回 (返回码, 标准输出文本)。失败返回 (None, "")。"""
    git = 找git()
    if not git:
        return None, ""
    # core.quotepath=false：否则中文文件名会被转义成 \346\240\270 这种八进制
    命令 = [git, "-c", "core.quotepath=false", "-C", 目录] + list(参数)
    try:
        r = subprocess.run(
            命令,
            capture_output=True,
            timeout=超时,
            creationflags=_无窗口标志(),
        )
    except (OSError, subprocess.SubprocessError):
        return None, ""
    出 = (r.stdout or b"").decode("utf-8", "replace")
    return r.returncode, 出


def 是仓库(目录):
    if not 目录 or not os.path.isdir(目录):
        return False
    码, _ = _跑(目录, ["rev-parse", "--is-inside-work-tree"])
    return 码 == 0


def 状态(目录):
    """读一次仓库状态。

    返回 dict：
        可用      bool   —— git 在、目录是仓库、命令跑通了
        原因      str    —— 不可用时的原因（给人看的一句话）
        分支      str
        改动      [(状态码, 路径), …]  状态码是 'M'/'A'/'??' 这类两字符码
        领先       int    —— 本地比上游多的提交数
        落后       int    —— 上游比本地多的提交数
        有上游    bool
    """
    结果 = {
        "可用": False,
        "原因": "",
        "分支": "",
        "改动": [],
        "领先": 0,
        "落后": 0,
        "有上游": False,
    }
    if not os.path.isdir(目录 or ""):
        结果["原因"] = "目录不存在"
        return 结果
    if not 找git():
        结果["原因"] = "没找到 git"
        return 结果
    if not 是仓库(目录):
        结果["原因"] = "这里不是 git 仓库"
        return 结果

    码, 出 = _跑(目录, ["rev-parse", "--abbrev-ref", "HEAD"])
    if 码 != 0:
        结果["原因"] = "读不到当前分支"
        return 结果
    结果["分支"] = 出.strip() or "(未知)"
    结果["可用"] = True

    码, 出 = _跑(目录, ["status", "--porcelain"])
    if 码 == 0:
        改动 = []
        for 行 in 出.splitlines():
            if not 行.strip():
                continue
            # porcelain v1：前两列是状态码，第三列起是路径
            码位 = 行[:2]
            路径 = 行[3:] if len(行) > 3 else ""
            if 路径.startswith('"') and 路径.endswith('"'):
                路径 = 路径[1:-1]
            改动.append((码位, 路径))
        结果["改动"] = 改动

    # 和上游的差距。没有上游（比如新建分支、没配 remote）就跳过。
    码, 出 = _跑(目录, ["rev-list", "--left-right", "--count", "@{upstream}...HEAD"])
    if 码 == 0:
        部分 = 出.split()
        if len(部分) == 2:
            try:
                结果["落后"] = int(部分[0])
                结果["领先"] = int(部分[1])
                结果["有上游"] = True
            except ValueError:
                pass
    return 结果


#: porcelain v1 的两列含义不同：
#:   第 1 列 = 暂存区（index）相对 HEAD 的状态
#:   第 2 列 = 工作区（worktree）相对暂存区的状态
#: 所以 'M '（已暂存）和 ' M'（已修改）不是一回事，必须分开翻译。
暂存区说明 = {
    "M": "已暂存",
    "A": "新增已暂存",
    "D": "删除已暂存",
    "R": "重命名已暂存",
    "C": "复制已暂存",
    "T": "类型已变更",
}
工作区说明 = {
    "M": "已修改",
    "A": "新增",
    "D": "已删除",
    "R": "已重命名",
    "C": "已复制",
    "T": "类型已变更",
}

#: 颜色键（对应主题表里的键名），给以后上色留的钩子
颜色键 = {
    "已暂存": "新增",
    "新增已暂存": "新增",
    "删除已暂存": "删除",
    "重命名已暂存": "改动",
    "复制已暂存": "新增",
    "类型已变更": "改动",
    "已修改": "改动",
    "新增": "新增",
    "已删除": "删除",
    "已重命名": "改动",
    "已复制": "新增",
    "未跟踪": "新增",
    "已忽略": "忽略",
    "冲突": "冲突",
    "有改动": "改动",
}


def 说明状态(码位):
    """把 porcelain 的两字符状态码翻译成 (中文说明, 颜色键)。"""
    码位 = (码位 or "  ").ljust(2)[:2]
    if 码位 == "??":
        return ("未跟踪", "新增")
    if 码位 == "!!":
        return ("已忽略", "忽略")
    # 冲突：任一列是 U，或两列都是 A/D
    if "U" in 码位 or 码位 in ("AA", "DD"):
        return ("冲突", "冲突")
    暂, 工 = 码位[0], 码位[1]
    if 暂 != " ":
        名 = 暂存区说明.get(暂, "已暂存")
        return (名, 颜色键.get(名, "改动"))
    if 工 != " ":
        名 = 工作区说明.get(工, "已修改")
        return (名, 颜色键.get(名, "改动"))
    return ("有改动", "改动")


def 摘要(状态字典):
    """按钮/状态栏上那一行短文字，例如「⎇ main  ✚3」。"""
    if not 状态字典.get("可用"):
        return "⎇ 未启用"
    分支 = 状态字典.get("分支") or "?"
    改 = len(状态字典.get("改动") or [])
    尾 = ""
    if 改:
        尾 += "  ✚%d" % 改
    if 状态字典.get("领先"):
        尾 += "  ↑%d" % 状态字典["领先"]
    if 状态字典.get("落后"):
        尾 += "  ↓%d" % 状态字典["落后"]
    return "⎇ %s%s" % (分支, 尾)
