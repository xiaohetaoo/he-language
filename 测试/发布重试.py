# -*- coding: utf-8 -*-
"""持续重试发布 Release，直到网络窗口出现。

当前网络对 api.github.com 的多数 IP 有阻断，但偶尔会有几秒可用。
这个脚本会在多个 IP 之间轮询，一旦连上就完成发布。

用法：
    set GH_TOKEN=...
    python 测试/发布重试.py
    python 测试/发布重试.py --最多 60       最多重试 60 轮
    python 测试/发布重试.py --草稿          建成草稿
"""

import importlib.util
import os
import sys
import time

这里 = os.path.dirname(os.path.abspath(__file__))
根目录 = os.path.dirname(这里)
sys.path.insert(0, 根目录)

令牌 = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
if not 令牌:
    print("缺少 GH_TOKEN")
    sys.exit(2)

spec = importlib.util.spec_from_file_location(
    "发布Release", os.path.join(这里, "发布Release.py")
)
发布 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(发布)

import 核  # noqa: E402

IP列表 = os.environ.get("HE_API_IPS", "").replace(";", ",")
IP列表 = [x.strip() for x in IP列表.split(",") if x.strip()] or [
    "140.82.112.6", "140.82.113.6", "140.82.114.6", "140.82.116.6",
    "140.82.121.6", "140.82.112.5", "20.205.243.168",
]
最多 = 60
if "--最多" in sys.argv:
    最多 = int(sys.argv[sys.argv.index("--最多") + 1])


def 试一次():
    """换一个 IP 试 /user；返回 True 表示这一刻网络可用。"""
    for ip in IP列表:
        os.environ["HE_API_IPS"] = ip
        os.environ["HE_DIRECT"] = "1"
        码, 结果 = 发布.请求("GET", "/user", 令牌, 超时=3)
        if 码 == 200:
            print("  可用 IP：%s（登录名 %s）" % (ip, 结果.get("login")))
            return ip
    return None


def 主():
    版本号 = 核.版本
    print("目标：v%s" % 版本号)
    print("在 %d 个 IP 之间轮询，最多 %d 轮…" % (len(IP列表), 最多))
    可用 = None
    for 轮 in range(1, 最多 + 1):
        print("第 %d 轮" % 轮)
        可用 = 试一次()
        if 可用:
            break
        time.sleep(2)
    if not 可用:
        print("\n一直没连上 api.github.com。")
        print("建议换个网络（手机热点等）再执行：")
        print("  set GH_TOKEN=...")
        print("  python 测试/发布Release.py")
        return 1

    # 网络可用，立刻发布（沿用同一个 IP）
    os.environ["HE_API_IPS"] = 可用
    os.environ["HE_DIRECT"] = "1"
    print("\n开始发布…")
    原始argv = sys.argv
    try:
        sys.argv = [原始argv[0]] + [a for a in 原始argv[1:] if not a.startswith("--最多")]
        return 发布.主()
    finally:
        sys.argv = 原始argv


if __name__ == "__main__":
    sys.exit(主())
