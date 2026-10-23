# -*- coding: utf-8 -*-
"""验证打包后的 exe：--内核 能跑真实程序、能报错、能跑交互输入。"""
import os
import subprocess
import sys
import tempfile

这里 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
exe = os.path.join(这里, "dist", "核工坊Qt.exe")

失败 = []


def 跑(名, 源码, 输入=None, 期望=None):
    目录 = tempfile.mkdtemp(prefix="核exe_")
    路径 = os.path.join(目录, "测试.xht")
    with open(路径, "w", encoding="utf-8", newline="\n") as f:
        f.write(源码)
    环境 = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    结果 = subprocess.run(
        [exe, "--内核", 路径],
        input=(输入.encode() if 输入 else None),
        capture_output=True, timeout=90, env=环境,
    )
    出 = 结果.stdout.decode("utf-8", "replace") + 结果.stderr.decode("utf-8", "replace")
    ok = True
    if 期望 is not None:
        ok = 期望 in 出
    print("  %-16s 码=%d %s%s" % (名, 结果.returncode, "OK" if ok else "FAIL",
                                  "" if ok else "  输出:" + 出.strip()[:200]))
    if not ok:
        失败.append(名)


print("=== exe 内核功能 ===")
跑("hello", '核说("你好，世界")\n', 期望="你好，世界")
跑("算术循环", '核用 i 遍历 核数列(1, 4)：\n    核说(i * i)\n', 期望="9")
跑("中文函数", '核定义 加(a, b)：\n    核返回 a + b\n核说(加(2, 3))\n', 期望="5")
跑("容器", 'x = 核列表([3, 1, 2])\nx.核排序()\n核说(x)\n', 期望="[1, 2, 3]")
跑("f-string", '名 = "核"\n核说(核"你好 {名}")\n', 期望="你好 核")
跑("异常", '核试：\n    核说(1 / 0)\n核异常 除零错误：\n    核说("除零了")\n', 期望="除零了")
跑("交互输入", '核说(说核())\n', 输入="小明\n", 期望="小明")
跑("语法错误", '核说(1 +\n', 期望="语法")
跑("运行时错误", '核说(1 / 0)\n', 期望="")

# 版本
结果 = subprocess.run([exe, "--内核", "--版本"], capture_output=True, timeout=60,
                     env=dict(os.environ, PYTHONIOENCODING="utf-8"))
出 = (结果.stdout + 结果.stderr).decode("utf-8", "replace")
ok = "0.0.8" in 出
print("  %-16s %s  %s" % ("版本查询", "OK" if ok else "FAIL", 出.strip()[:80]))
if not ok:
    失败.append("版本查询")

print("\n结果:", "全部通过" if not 失败 else "失败 %s" % 失败)
sys.exit(0 if not 失败 else 1)
