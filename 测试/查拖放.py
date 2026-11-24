# -*- coding: utf-8 -*-
"""拖放模块的引用管理（不开真实窗口，只验状态机）。

盯两个曾经的真问题：
1. 释放拖放(根窗口) 里用了模块级根本没有的 ctypes/wintypes，
   每次 NameError 被自己的 except 吞掉 —— 「释放」永远没生效，
   模块级容器只增不减。
2. 启用拖放 里调 释放拖放(全部=True)，把**别的窗口**的回调引用也清了，
   而那些窗口的窗口过程还指着我们的回调 —— 回调一被回收就是野指针。

用法：python 测试/查拖放.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import 拖放  # noqa: E402

问题 = []


def 检(条件, 说明):
    if 条件:
        print("  ok   %s" % 说明)
    else:
        问题.append(说明)
        print("  !!   %s" % 说明)


class 假窗:
    """只实现 winfo_id()，够 释放拖放 用，且不需要真的 Tk 窗口。"""

    def __init__(self, 号):
        self.号 = 号

    def winfo_id(self):
        return self.号


if not 拖放.可用:
    print("非 Windows，拖放本就降级为不可用 —— 跳过")
    sys.exit(0)

检(hasattr(拖放, "ctypes") and 拖放.ctypes is not None,
   "模块级有 ctypes（释放拖放 要用它）")
检(hasattr(拖放, "wintypes") and 拖放.wintypes is not None,
   "模块级有 wintypes")

# 造两个「已启用」的窗口状态。原过程给 None：_撤掉 就不会真去调
# SetWindowLongPtrW，也就不会碰到不属于本测试的窗口。
拖放._已启用.clear()
拖放._原过程.clear()
拖放._回调引用.clear()
for 号 in (111, 222):
    拖放._已启用.add(号)
    拖放._原过程[号] = None
    拖放._回调引用[号] = "回调%d" % 号

print("== 一、释放单个窗口 ==")
拖放.释放拖放(假窗(111))
检(111 not in 拖放._已启用, "目标句柄从 _已启用 里摘掉了")
检(111 not in 拖放._原过程, "目标句柄的原过程指针清掉了")
检(111 not in 拖放._回调引用, "目标句柄的回调引用释放了")
检(222 in 拖放._已启用 and 222 in 拖放._回调引用,
   "另一个窗口的状态原样留着（清掉它就是野指针）")

print("== 二、全部释放 ==")
拖放.释放拖放(全部=True)
检(not 拖放._已启用 and not 拖放._原过程 and not 拖放._回调引用,
   "三个容器都清空了")

print("== 三、拿不到句柄时不许抛 ==")
try:
    拖放.释放拖放(None)
    拖放.释放拖放(假窗(999))
    检(True, "空窗口 / 没注册过的句柄都安静返回")
except Exception as e:  # noqa: BLE001
    检(False, "释放拖放 抛了 %r" % e)

print()
print("=" * 62)
if 问题:
    print("发现 %d 处拖放引用管理问题：" % len(问题))
    for 说明 in 问题:
        print("  · %s" % 说明)
    sys.exit(1)
print("拖放引用管理正常")