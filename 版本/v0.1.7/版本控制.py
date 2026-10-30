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


def 无窗口标志():
    """Windows 上别弹出黑色控制台窗口。

    GUI 程序里调 subprocess 若不设这个标志，每次起子进程都会闪一下 cmd
    窗口，用户会以为程序在乱开窗口。核工坊也用这一份（跑用户程序时的
    Popen）—— 以前只在 git 调用上修过，运行用户程序那处漏了。
    """
    if sys.platform != "win32":
        return 0
    return getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)


#: 旧名，保留给可能还在引用的地方
_无窗口标志 = 无窗口标志


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
            creationflags=无窗口标志(),
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
            # 重命名/复制写成 "旧名 -> 新名"（v1 不带 -z 的固定格式）。
            # 原样存下来的话，双击打开会拿 目录/「旧名 -> 新名」去当路径，
            # 必然找不到文件。只留新名 —— 那是现在真实存在的那个。
            if "R" in 码位 or "C" in 码位:
                旧名, 箭头, 新名 = 路径.partition(" -> ")
                if 箭头 and 新名:
                    路径 = 新名
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


#: 单个文件的 diff 最多取这么多行，超了就截断并注明。
#: 为什么要截：一个刚格式化过的大文件能产出几万行 diff，
#: 全塞进 QPlainTextEdit 会让界面卡住。看全量还是去 git 客户端。
diff行数上限 = 4000


def 取差异(目录, 相对路径):
    """取单个文件相对 HEAD 的 diff（只读），返回 (文本, 说明)。

    返回的 文本 一律是统一 diff 格式；说明 是给用户看的一句话
    （成功时为空串，失败时说明为什么没有 diff）。
    """
    if not 目录 or not os.path.isdir(目录):
        return "", "目录不存在"
    相对路径 = (相对路径 or "").strip()
    if not 相对路径:
        return "", "没有指定文件"

    # 一次 `git diff HEAD` 就能看全「暂存 + 未暂存」两部分。
    #
    # 以前先跑 `git diff`（只看工作区相对暂存区），**只有当它为空**
    # 才回看 `--cached`。于是「已 git add 之后又改了一笔」的文件
    # 只显示后面那一笔，暂存部分完全看不到 —— 用户以为就改了这么多。
    # `git diff HEAD` 是工作区相对 HEAD，两笔都在里面。
    码, 出 = _跑(
        目录,
        ["diff", "HEAD", "--no-color", "--", 相对路径],
    )
    if 码 != 0:
        # HEAD 不存在（新仓库、还没第一次提交）时 diff HEAD 会失败，
        # 退回工作区 diff —— 否则新库里所有文件都显示「读不到 diff」。
        码, 出 = _跑(
            目录,
            ["diff", "--no-color", "--", 相对路径],
        )
        if 码 != 0:
            return "", "读不到 diff（git 返回 %s）" % 码
    文本 = 出

    if not 文本.strip():
        # 未跟踪文件（git diff 完全不管它们）。
        # 未跟踪时直接把文件内容按「新增」格式摆出来 ——
        # 用户点开一个刚建的文件，看到空白一片毫无意义。
        新 = _未跟踪内容(目录, 相对路径)
        if 新 is not None:
            return 新, "（未跟踪的新文件，下面是它的全部内容）"
        return "", "这个文件没有可显示的差异（可能是未跟踪，或内容已提交）"
    else:
        说明 = ""

    行集 = 文本.splitlines()
    if len(行集) > diff行数上限:
        文本 = "\n".join(行集[:diff行数上限])
        文本 += "\n… 已截断（共 %d 行，只显示前 %d 行）" % (len(行集), diff行数上限)
        说明 = (说明 + " " if 说明 else "") + "内容过长已截断"
    return 文本, 说明

def _未跟踪内容(目录, 相对路径, 上限=None):
    """未跟踪文件的「新增」式 diff；不是未跟踪则返回 None。

    只在文件能读、且确实是未跟踪时才返回内容。目录、二进制、
    读不到一律返回 None，交给调用方给普通提示。

    上限 默认取 diff行数上限，运行时读模块变量 —— 不写作默认参数，
    因为默认参数在函数定义时就求值，会把值焊死在那个时刻。
    """
    if 上限 is None:
        上限 = diff行数上限
    全 = os.path.join(目录, 相对路径)
    if not os.path.isfile(全):
        return None
    码, _出 = _跑(目录, ["ls-files", "--error-unmatch", "--", 相对路径])
    if 码 == 0:
        return None  # 已被 git 跟踪，不是未跟踪文件
    try:
        with open(全, "rb") as f:
            原 = f.read()
    except OSError:
        return None
    # 二进制文件不往文本框里塞
    if b"\x00" in 原[:1024]:
        return None
    # 编码：先 UTF-8，再试 GB18030（兼容 GBK/GB2312）。
    # 以前只认 UTF-8，GBK 编码的文件直接判「读不到」→ 面板显示
    # 「没有可显示的差异」，用户以为文件真的没改动（实测）。
    # GB18030 是超集，能覆盖绝大多数中文 Windows 下保存的文本。
    文本 = None
    for 编码 in ("utf-8", "gb18030"):
        try:
            文本 = 原.decode(编码)
            break
        except UnicodeDecodeError:
            continue
    if 文本 is None:
        return None
    行集 = 文本.splitlines()
    头 = ["--- /dev/null", "+++ b/%s" % 相对路径, "@@ 新文件 @@"]
    体 = ["+%s" % 行 for 行 in 行集]
    if len(行集) > 上限:
        体 = 体[:上限]
        体.append("… 已截断（共 %d 行，只显示前 %d 行）" % (len(行集), 上限))
    return "\n".join(头 + 体)
