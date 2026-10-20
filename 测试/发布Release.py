# -*- coding: utf-8 -*-
"""创建 GitHub Release 并上传 exe 附件。

GitHub 的 Release/附件接口需要 Personal Access Token（SSH 密钥不能用于 API）。
请先在 GitHub 生成 token：Settings → Developer settings → Personal access
tokens → Fine-grained tokens，权限给 「Contents: Read and write」 即可。

用法（token 只用于本次调用，不写入任何文件）：

    set GH_TOKEN=github_pat_xxx
    python 测试/发布Release.py

或：

    python 测试/发布Release.py --token github_pat_xxx

可选参数：
    --标签 v0.0.1        指定 tag（默认读 核.py 的版本号）
    --附件 dist/核工坊.exe,说明.md
    --草稿               创建为草稿，先预览再发布
"""

import json
import os
import sys
import urllib.error
import urllib.request

这里 = os.path.dirname(os.path.abspath(__file__))
根目录 = os.path.dirname(这里)
sys.path.insert(0, 根目录)

import 核  # noqa: E402

仓库 = "xiaohetaoo/he-language"
接口 = "https://api.github.com"


def 请求(方法, 路径, 令牌, 数据=None, 原始=None, 类型=None):
    地址 = 接口 + 路径
    if 原始 is not None:
        体 = 原始
        headers = {
            "Authorization": "Bearer %s" % 令牌,
            "Accept": "application/vnd.github+json",
            "Content-Type": 类型 or "application/octet-stream",
            "X-GitHub-Api-Version": "2022-11-28",
        }
    else:
        体 = json.dumps(数据).encode("utf-8") if 数据 is not None else None
        headers = {
            "Authorization": "Bearer %s" % 令牌,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if 体:
            headers["Content-Type"] = "application/json"
    请求对象 = urllib.request.Request(地址, data=体, headers=headers, method=方法)
    try:
        with urllib.request.urlopen(请求对象, timeout=180) as 响应:
            内容 = 响应.read()
            return 响应.status, (json.loads(内容) if 内容 else {})
    except urllib.error.HTTPError as e:
        细节 = e.read().decode("utf-8", "replace")
        return e.code, {"错误": 细节}
    except Exception as e:  # noqa: BLE001
        return 0, {"错误": str(e)}


def 读发布说明(版本):
    """从 版本记录.md 里取该版本的段落作为 Release 说明。"""
    路径 = os.path.join(根目录, "版本记录.md")
    要点 = []
    if os.path.exists(路径):
        with open(路径, encoding="utf-8") as f:
            行集 = f.readlines()
        收录 = False
        for 行 in 行集:
            if 行.startswith("## %s 详细说明" % 版本):
                收录 = True
                continue
            if 收录 and 行.startswith("## "):
                break
            if 收录:
                要点.append(行.rstrip())
    if not 要点:
        要点 = ["核语言首个版本。", "", "详见仓库 README 与 说明.md。"]
    return "\n".join(要点).strip()


def 主():
    参数 = sys.argv[1:]
    令牌 = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if "--token" in 参数:
        令牌 = 参数[参数.index("--token") + 1]
    if not 令牌:
        print("缺少令牌。请先设置环境变量 GH_TOKEN，或用 --token 传入。")
        print("生成地址：https://github.com/settings/tokens （需要 Contents 读写权限）")
        return 2

    版本 = "v%s" % 核.版本
    if "--标签" in 参数:
        版本 = 参数[参数.index("--标签") + 1]

    附件 = os.path.join(根目录, "dist", "核工坊.exe")
    if "--附件" in 参数:
        附件 = 参数[参数.index("--附件") + 1]

    说明 = 读发布说明(版本.lstrip("v"))
    草稿 = "--草稿" in 参数

    print("仓库：%s" % 仓库)
    print("标签：%s" % 版本)
    print("附件：%s（%s）" % (附件, "存在" if os.path.exists(附件) else "缺失"))

    码, 结果 = 请求("GET", "/repos/%s/releases/tags/%s" % (仓库, 版本), 令牌)
    if 码 == 200:
        print("该标签的 Release 已存在：%s" % 结果.get("html_url"))
        return 0
    if 码 not in (404,):
        print("查询失败（%s）：%s" % (码, 结果))
        return 1

    码, 结果 = 请求(
        "POST",
        "/repos/%s/releases" % 仓库,
        令牌,
        数据={
            "tag_name": 版本,
            "name": "核语言 %s" % 版本.lstrip("v"),
            "body": 说明,
            "draft": 草稿,
            "prerelease": False,
        },
    )
    if 码 not in (200, 201):
        print("创建 Release 失败（%s）：%s" % (码, 结果))
        if 码 == 403:
            print("\n提示：令牌缺少 Contents 写权限。")
        return 1

    发布 = 结果
    print("Release 已创建：%s" % 发布.get("html_url"))

    if os.path.exists(附件):
        名 = os.path.basename(附件)
        地址 = 发布.get("upload_url", "").split("{")[0]
        地址 += "?name=%s" % urllib.parse.quote(名)
        类型 = "application/octet-stream"
        if 名.endswith(".exe"):
            类型 = "application/vnd.microsoft.portable-executable"
        with open(附件, "rb") as f:
            体 = f.read()
        print("上传 %s（%.1f MB）…" % (名, len(体) / 1024 / 1024))
        码, 结果 = 请求(
            "POST",
            "",
            令牌,
            原始=体,
            类型=类型,
        ) if 地址.startswith(接口) else (None, None)
        if 码 is None:
            # upload_url 是绝对地址，直接用它
            请求对象 = urllib.request.Request(
                地址,
                data=体,
                headers={
                    "Authorization": "Bearer %s" % 令牌,
                    "Accept": "application/vnd.github+json",
                    "Content-Type": 类型,
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(请求对象, timeout=600) as 响应:
                    结果 = json.loads(响应.read() or b"{}")
                    码 = 响应.status
            except urllib.error.HTTPError as e:
                码 = e.code
                结果 = {"错误": e.read().decode("utf-8", "replace")}
            except Exception as e:  # noqa: BLE001
                码 = 0
                结果 = {"错误": str(e)}
        if 码 in (200, 201):
            print("附件已上传：%s" % 结果.get("browser_download_url", ""))
        else:
            print("附件上传失败（%s）：%s" % (码, 结果))

    print("\n完成。发布页：%s" % 发布.get("html_url"))
    return 0


if __name__ == "__main__":
    import urllib.parse  # noqa: E402

    sys.exit(主())
