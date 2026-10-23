# -*- coding: utf-8 -*-
"""创建 GitHub Release 并上传 exe。

GitHub 的 Release 与附件接口需要 Personal Access Token
（SSH 密钥只能用于 git push，不能调 API）。

用法：
    set GH_TOKEN=github_pat_xxx
    python 测试/发布Release.py

    python 测试/发布Release.py --token github_pat_xxx
    python 测试/发布Release.py --草稿              先建草稿，预览后再发布
    python 测试/发布Release.py --源码包            额外附上源码 zip

行为约定：
  · exe 不存在就直接失败 —— 发布一个没有 exe 的 Release 没有意义
  · Release 若已存在，不重复创建，只补齐缺失的附件
  · 附件传完后再查一次，确认真在页面上
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile

这里 = os.path.dirname(os.path.abspath(__file__))
根目录 = os.path.dirname(这里)
sys.path.insert(0, 根目录)

import 核  # noqa: E402

仓库 = "xiaohetaoo/he-language"
接口 = "https://api.github.com"
版本文件 = "版本信息.txt"


def _头(令牌):
    return {
        "Authorization": "Bearer %s" % 令牌,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        # GitHub 强制要求 User-Agent，缺了会直接 403
        "User-Agent": "he-language-release-script",
    }


def _直连请求(方法, 地址, 头, 体, 超时, 进度=False):
    """绕开 DNS，直接用可用 IP 连 api.github.com。

    某些网络会把 api.github.com 的某个 IP 屏蔽（DNS 只返回那一个），
    但同一域名在别的 IP 上是通的。这里按 IP 建立 TCP，TLS 里仍用
    api.github.com 作 SNI/Host，校验照常做，安全性不打折。

    `体` 可以是 bytes，也可以是「能以 read(n) 分块读的对象」。
    后者用于上传大文件：107MB 的 exe 如果一次性 sendall，
    在慢速链路上必定超过超时（实测 900 秒都没传完），
    而且会先把整个文件读进内存。分块发送既省内存又能报进度。
    """
    import socket
    import ssl
    from urllib.parse import urlsplit

    解析 = urlsplit(地址)
    主机 = 解析.hostname or "api.github.com"
    路径 = 解析.path or "/"
    if 解析.query:
        路径 += "?" + 解析.query
    # 非 ASCII 字符必须在请求行里百分号编码，否则服务器会把文件名解析成空
    # （曾出现上传中文名 exe 后变成 default.exe）
    if not 路径.isascii():
        路径 = urllib.parse.quote(路径, safe="/?=&%:+,")

    # 主机不同，能用的 IP 也不同：上传走 uploads.github.com，
    # 它的 IP 与 api.github.com 不是同一组，混用会得到 404。
    if os.environ.get("HE_API_IPS"):
        候选 = [IP.strip() for IP in os.environ["HE_API_IPS"].replace(";", ",").split(",") if IP.strip()]
    else:
        候选 = []
    try:
        import socket as _socket

        候选.insert(0, _socket.gethostbyname(主机))
    except Exception:  # noqa: BLE001
        pass
    if 主机.startswith("uploads."):
        候选 += ["20.205.243.161", "20.205.243.162", "20.205.243.163"]
    else:
        候选 += [
            "140.82.112.6", "140.82.113.6", "140.82.114.6", "140.82.116.6",
            "140.82.121.6", "20.205.243.168",
        ]
    流式 = hasattr(体, "read")
    if 流式:
        总长 = 体.seek(0, 2)
        体.seek(0)
    else:
        总长 = len(体) if 体 else 0
    上次错误 = ""
    for IP in 候选:
        IP = IP.strip()
        if not IP:
            continue
        try:
            if 流式:
                体.seek(0)
            上下文 = ssl.create_default_context()
            # 先用很短的超时探测端口，不通就立刻换下一个，
            # 否则一个死 IP 会拖住 30 秒（多个候选累积起来像卡死）。
            原始 = socket.create_connection((IP, 443), timeout=3)
            # 注意：这里必须用调用方给的超时，不要 min(超时,60)。
            # 上传 107MB 时 60 秒根本不够，会被误判为「所有 IP 都连不上」。
            原始.settimeout(超时)
            套 = 上下文.wrap_socket(原始, server_hostname=主机)
            try:
                行集 = [
                    "%s %s HTTP/1.1" % (方法, 路径),
                    "Host: %s" % 主机,
                ]
                for 键, 值 in 头.items():
                    if 键.lower() in ("host", "content-length"):
                        continue
                    行集.append("%s: %s" % (键, 值))
                行集.append("Content-Length: %d" % 总长)
                行集.append("Connection: close")
                行集.append("")
                套.sendall(("\r\n".join(行集) + "\r\n").encode("utf-8"))
                if 总长:
                    if 流式:
                        已发 = 0
                        上次报 = 0
                        while True:
                            块 = 体.read(1024 * 256)
                            if not 块:
                                break
                            套.sendall(块)
                            已发 += len(块)
                            if 进度 and 已发 - 上次报 >= 总长 // 10:
                                上次报 = 已发
                                print("    上传 %.0f%%（%.1f/%.1f MB）"
                                      % (已发 * 100.0 / 总长, 已发 / 1048576.0,
                                         总长 / 1048576.0), flush=True)
                    else:
                        套.sendall(体)
                数据 = b""
                while True:
                    块 = 套.recv(65536)
                    if not 块:
                        break
                    数据 += 块
            finally:
                套.close()
            状态行, _, 剩余 = 数据.partition(b"\r\n")
            头部, _, 正文 = 剩余.partition(b"\r\n\r\n")
            码 = int(状态行.split(b" ")[1])
            # 处理分块传输
            头文 = 头部.decode("latin1").lower()
            if "transfer-encoding: chunked" in 头文:
                正文 = _解分块(正文)
            try:
                结果 = json.loads(正文) if 正文 else {}
            except Exception:  # noqa: BLE001
                结果 = {"原始": 正文[:200].decode("utf-8", "replace")}
            return 码, 结果
        except Exception as e:  # noqa: BLE001
            上次错误 = "%s@%s 失败：%s" % (主机, IP, type(e).__name__)
            continue
    return 0, {"错误": "所有 IP 都连不上（%s）" % 上次错误}


def _解分块(数据):
    """解 HTTP chunked 编码。"""
    结果 = b""
    while 数据:
        行尾 = 数据.find(b"\r\n")
        if 行尾 < 0:
            break
        try:
            长度 = int(数据[:行尾].split(b";")[0], 16)
        except ValueError:
            break
        if 长度 == 0:
            break
        结果 += 数据[行尾 + 2: 行尾 + 2 + 长度]
        数据 = 数据[行尾 + 2 + 长度 + 2:]
    return 结果


def 请求(方法, 路径, 令牌, 数据=None, 原始=None, 类型=None, 超时=60, 进度=False):
    """调 GitHub API；返回 (状态码, 解析结果)。

    先走普通 urllib；如果连不上（常见于 api.github.com 被屏蔽），
    自动退回「直连可用 IP」的方式重试。

    `原始` 可以是 bytes 或已打开的文件对象。文件对象会走流式直连上传：
    107MB 一次性 sendall 在慢链路上必然超时，而且 urllib 也没法报进度。
    """
    地址 = 路径 if 路径.startswith("http") else 接口 + 路径
    头 = _头(令牌)
    流式 = 原始 is not None and hasattr(原始, "read")
    if 原始 is not None:
        头["Content-Type"] = 类型 or "application/octet-stream"
        体 = 原始
    elif 数据 is not None:
        头["Content-Type"] = "application/json"
        体 = json.dumps(数据).encode("utf-8")
    else:
        体 = None

    # 大文件上传：不管环境变量，直接走流式直连。
    if 流式 or os.environ.get("HE_DIRECT") == "1":
        return _直连请求(方法, 地址, 头, 体, 超时, 进度=进度)

    请求对象 = urllib.request.Request(地址, data=体, headers=头, method=方法)
    try:
        with urllib.request.urlopen(请求对象, timeout=超时) as 响应:
            内容 = 响应.read()
            return 响应.status, (json.loads(内容) if 内容 else {})
    except urllib.error.HTTPError as e:
        原文 = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(原文)
        except Exception:  # noqa: BLE001
            return e.code, {"错误": 原文}
    except Exception as e:  # noqa: BLE001
        码, 结果 = _直连请求(方法, 地址, 头, 体, 超时, 进度=进度)
        if 码:
            print("（已改用直连 IP 访问）")
            return 码, 结果
        return 0, {"错误": "%s: %s" % (type(e).__name__, e)}


def 读发布说明(版本号):
    """取 版本记录.md 里该版本的段落作为 Release 说明。"""
    路径 = os.path.join(根目录, "版本记录.md")
    要点 = []
    if os.path.exists(路径):
        with open(路径, encoding="utf-8") as f:
            行集 = f.readlines()
        收录 = False
        for 行 in 行集:
            if 行.startswith("## %s 详细说明" % 版本号):
                收录 = True
                continue
            if 收录 and 行.startswith("## "):
                break
            if 收录:
                要点.append(行.rstrip())
    正文 = "\n".join(要点).strip()
    if not 正文:
        正文 = "详见仓库 README.md 与 说明.md。"
    return 正文


def 打源码包(输出):
    """把源码打成一个 zip，方便只想看代码的人。"""
    跳过目录 = {".git", "__pycache__", "build", "dist", "版本", ".vscode", ".idea"}
    with zipfile.ZipFile(输出, "w", zipfile.ZIP_DEFLATED) as z:
        for 根, 目录集, 文件集 in os.walk(根目录):
            目录集[:] = [d for d in 目录集 if d not in 跳过目录]
            for 名 in 文件集:
                if 名.endswith((".pyc", ".spec")) or 名 == "工坊配置.json":
                    continue
                全 = os.path.join(根, 名)
                相对 = os.path.relpath(全, 根目录)
                z.write(全, os.path.join("he-language-%s" % 核.版本, 相对))
    return 输出


def 上传附件(发布, 令牌, 路径, 名=None):
    """上传一个附件，返回 (是否成功, 说明)。

    `名` 是发布到页面上的文件名，必须纯 ASCII —— GitHub 会把非 ASCII
    文件名解析成 default.exe（以前上传「核工坊.exe」就踩过）。
    """
    名 = 名 or os.path.basename(路径)
    已有 = {a.get("name") for a in 发布.get("assets", [])}
    if 名 in 已有:
        return True, "已存在，跳过：%s" % 名

    上传地址 = (发布.get("upload_url") or "").split("{")[0]
    if not 上传地址:
        return False, "拿不到 upload_url"
    上传地址 += "?name=%s" % urllib.parse.quote(名)

    类型 = "application/octet-stream"
    if 名.lower().endswith(".exe"):
        类型 = "application/vnd.microsoft.portable-executable"
    elif 名.lower().endswith(".zip"):
        类型 = "application/zip"

    大小兆 = os.path.getsize(路径) / 1024.0 / 1024.0
    print("  正在上传 %s（%.1f MB）…" % (名, 大小兆), flush=True)
    # 用文件对象而不是 bytes：107MB 一次性读进内存再发，在慢链路上
    # 必然超时（实测 900 秒没传完），而且看不到进度。
    with open(路径, "rb") as f:
        码, 结果 = 请求("POST", 上传地址, 令牌, 原始=f, 类型=类型,
                        超时=1800, 进度=True)
    if 码 in (200, 201):
        return True, "已上传 %s（%.1f MB）→ %s" % (
            名, 大小兆, 结果.get("browser_download_url", "")
        )
    return False, "上传 %s 失败（%s）：%s" % (名, 码, 结果)


def 从凭据管理器取令牌():
    """尝试从 git 的凭据管理器里取 GitHub token。

    能取到就直接用；取到但无效会被 API 拒（401），那种情况需要重新生成。
    """
    import subprocess

    try:
        结果 = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n\n",
            capture_output=True,
            text=True,
            cwd=根目录,
            timeout=20,
        )
    except Exception:  # noqa: BLE001
        return None
    for 行 in (结果.stdout or "").splitlines():
        if 行.startswith("password="):
            值 = 行.split("=", 1)[1].strip()
            return 值 or None
    return None


def 主():
    参数 = sys.argv[1:]
    令牌 = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if "--token" in 参数:
        令牌 = 参数[参数.index("--token") + 1]
    if not 令牌 and "--凭据" in 参数:
        令牌 = 从凭据管理器取令牌()
        if 令牌:
            print("已从 git 凭据管理器取到令牌（%d 位）" % len(令牌))
    if not 令牌:
        print("缺少令牌 —— GitHub 的 Release 接口必须用 Personal Access Token。")
        print()
        print("生成步骤：")
        print("  1. 打开 https://github.com/settings/tokens?type=beta")
        print("  2. 新建 Fine-grained token，Repository access 选 he-language")
        print("  3. Permissions → Repository permissions → Contents: Read and write")
        print("  4. 生成后执行：  set GH_TOKEN=github_pat_xxx")
        print("                   python 测试/发布Release.py")
        return 2

    版本号 = 核.版本
    标签 = "v%s" % 版本号
    if "--标签" in 参数:
        标签 = 参数[参数.index("--标签") + 1]
    草稿 = "--草稿" in 参数

    附件清单 = []
    # 发布 Qt 版（0.0.6 起界面主推 Qt）。tkinter 版 核工坊.exe 仍然保留在
    # dist 里可回退，但不再作为发布物 —— 两个 exe 一起发会让用户不知道该下哪个。
    exe = os.path.join(根目录, "dist", "核工坊Qt.exe")
    if not os.path.exists(exe):
        print("找不到 %s —— 先执行 python 测试/打包Qt.py 生成 exe。" % exe)
        return 1
    # 附件名必须是纯 ASCII：GitHub 会把非 ASCII 文件名解析成 default.exe
    # （以前上传「核工坊.exe」就出现过这个情况）。命名沿用既有约定。
    发布名 = "HeLanguage-%s-win64.exe" % 版本号
    附件清单.append((exe, 发布名))
    if "--源码包" in 参数:
        zip路径 = os.path.join(根目录, "dist", "he-language-%s-src.zip" % 版本号)
        print("正在打源码包…")
        打源码包(zip路径)
        附件清单.append((zip路径, os.path.basename(zip路径)))

    print("仓库：%s" % 仓库)
    print("标签：%s" % 标签)
    print("附件：")
    for 本地, 名 in 附件清单:
        print("  %s → %s（%.1f MB）"
              % (os.path.basename(本地), 名,
                 os.path.getsize(本地) / 1024.0 / 1024.0))
    print()

    码, 发布 = 请求("GET", "/repos/%s/releases/tags/%s" % (仓库, 标签), 令牌)
    if 码 == 200:
        print("Release 已存在，只补附件：%s" % 发布.get("html_url"))
    elif 码 == 404:
        码, 发布 = 请求(
            "POST",
            "/repos/%s/releases" % 仓库,
            令牌,
            数据={
                "tag_name": 标签,
                "name": "核语言 %s" % 版本号,
                "body": 读发布说明(版本号),
                "draft": 草稿,
                "prerelease": False,
            },
        )
        if 码 not in (200, 201):
            print("创建 Release 失败（%s）：%s" % (码, 发布))
            if 码 == 403:
                print("\n提示：令牌需要 Contents 的写权限。")
            elif 码 == 422:
                print("\n提示：标签 %s 可能不存在，先 git push origin %s。" % (标签, 标签))
            return 1
        print("Release 已创建：%s" % 发布.get("html_url"))
    else:
        print("查询 Release 失败（%s）：%s" % (码, 发布))
        return 1

    print()
    全部成功 = True
    for 本地, 名 in 附件清单:
        成功, 说明 = 上传附件(发布, 令牌, 本地, 名)
        print(("  ✓ " if 成功 else "  × ") + 说明)
        全部成功 = 全部成功 and 成功

    # 上传后再查一次，确认真在页面上
    码, 复查 = 请求("GET", "/repos/%s/releases/tags/%s" % (仓库, 标签), 令牌)
    if 码 == 200:
        页面附件 = [a.get("name") for a in 复查.get("assets", [])]
        print("\n页面上现有附件：%s" % ("、".join(页面附件) or "（无）"))
        缺少 = [名 for _本地, 名 in 附件清单 if 名 not in 页面附件]
        if 缺少:
            全部成功 = False
            print("仍缺少：%s" % "、".join(缺少))

    print("\n发布页：%s" % 复查.get("html_url", 发布.get("html_url", "")))
    return 0 if 全部成功 else 1


if __name__ == "__main__":
    sys.exit(主())
