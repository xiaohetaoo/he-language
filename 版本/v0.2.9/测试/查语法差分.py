# -*- coding: utf-8 -*-
"""语法差分回归：同一语义的核语言程序与 Python 程序，输出必须逐字相同。

这一轮专挑第一轮没覆盖的语法角落：仅关键字参数、仅位置参数、
中文装饰器、魔术方法、元类、推导式作用域、增强赋值、字面量前缀等。

用法：python 测试/查语法差分.py
"""
import os
import re
import subprocess
import sys
import tempfile

根 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
核 = os.path.join(根, "核.py")

用例 = []


def 加(名, 中文, 英文):
    用例.append((名, 中文, 英文))


加("仅关键字参数", """
核定义 甲(a, *, b=2, c):
    核返回 a + b + c
核说(甲(1, c=3), 甲(1, b=10, c=3))
""", """
def 甲(a, *, b=2, c):
    return a + b + c
print(甲(1, c=3), 甲(1, b=10, c=3))
""")

加("仅位置参数", """
核定义 甲(a, b, /, c, *, d=4):
    核返回 (a, b, c, d)
核说(甲(1, 2, 3), 甲(1, 2, c=3, d=9))
""", """
def 甲(a, b, /, c, *, d=4):
    return (a, b, c, d)
print(甲(1, 2, 3), 甲(1, 2, c=3, d=9))
""")

加("中文名装饰器", """
核定义 记(函):
    核定义 包(*甲, **乙):
        核说("进")
        丙 = 函(*甲, **乙)
        核说("出")
        核返回 丙
    核返回 包
@记
核定义 算(x):
    核返回 x * 2
核说(算(5))
""", """
def 记(函):
    def 包(*甲, **乙):
        print("进")
        丙 = 函(*甲, **乙)
        print("出")
        return 丙
    return 包
@记
def 算(x):
    return x * 2
print(算(5))
""")

加("魔术方法", """
核类 袋:
    核定义 __init__(self, 甲):
        self.甲 = list(甲)
    核定义 __len__(self):
        核返回 len(self.甲)
    核定义 __getitem__(self, i):
        核返回 self.甲[i]
    核定义 __iter__(self):
        核返回 iter(self.甲)
    核定义 __contains__(self, x):
        核返回 x 核在 self.甲
    核定义 __repr__(self):
        核返回 "袋(%r)" % (self.甲,)
    核定义 __eq__(self, 他):
        核返回 self.甲 == 他.甲
    核定义 __call__(self, x):
        核返回 self.甲 + [x]
袋甲 = 袋([1, 2, 3])
核说(len(袋甲), 袋甲[1], 2 核在 袋甲, 9 核否 核在 袋甲)
核说([x 核用 x 遍历 袋甲], 袋甲 == 袋([1, 2, 3]), 袋甲(4), repr(袋甲))
""", """
class 袋:
    def __init__(self, 甲):
        self.甲 = list(甲)
    def __len__(self):
        return len(self.甲)
    def __getitem__(self, i):
        return self.甲[i]
    def __iter__(self):
        return iter(self.甲)
    def __contains__(self, x):
        return x in self.甲
    def __repr__(self):
        return "袋(%r)" % (self.甲,)
    def __eq__(self, 他):
        return self.甲 == 他.甲
    def __call__(self, x):
        return self.甲 + [x]
袋甲 = 袋([1, 2, 3])
print(len(袋甲), 袋甲[1], 2 in 袋甲, 9 not in 袋甲)
print([x for x in 袋甲], 袋甲 == 袋([1, 2, 3]), 袋甲(4), repr(袋甲))
""")

加("自定义上下文管理器", """
核类 管:
    核定义 __enter__(self):
        核说("开")
        核返回 self
    核定义 __exit__(self, 型, 值, 迹):
        核说("关", 型 核是 核空)
        核返回 核错
    核定义 做(self):
        核说("做")
核带 管() 核作为 甲:
    甲.做()
""", """
class 管:
    def __enter__(self):
        print("开")
        return self
    def __exit__(self, 型, 值, 迹):
        print("关", 型 is None)
        return False
    def 做(self):
        print("做")
with 管() as 甲:
    甲.做()
""")

加("元类", """
核类 元(type):
    核定义 __new__(cls, 名, 基, 典):
        典["记"] = 名
        核返回 super().__new__(cls, 名, 基, 典)
核类 甲(metaclass=元):
    核略过
核说(甲.记)
""", """
class 元(type):
    def __new__(cls, 名, 基, 典):
        典["记"] = 名
        return super().__new__(cls, 名, 基, 典)
class 甲(metaclass=元):
    pass
print(甲.记)
""")

加("多重继承MRO", """
核类 甲:
    核定义 说(self):
        核返回 "甲"
核类 乙(甲):
    核定义 说(self):
        核返回 "乙>" + super().说()
核类 丙(甲):
    核定义 说(self):
        核返回 "丙>" + super().说()
核类 丁(乙, 丙):
    核定义 说(self):
        核返回 "丁>" + super().说()
核说(丁().说())
核说([c.__name__ 核用 c 遍历 丁.__mro__])
""", """
class 甲:
    def 说(self):
        return "甲"
class 乙(甲):
    def 说(self):
        return "乙>" + super().说()
class 丙(甲):
    def 说(self):
        return "丙>" + super().说()
class 丁(乙, 丙):
    def 说(self):
        return "丁>" + super().说()
print(丁().说())
print([c.__name__ for c in 丁.__mro__])
""")

加("property与类方法", """
核类 温:
    甲 = 0
    核定义 __init__(self, 度):
        self._度 = 度
    @property
    核定义 度(self):
        核返回 self._度
    @度.setter
    核定义 度(self, v):
        self._度 = v
    @classmethod
    核定义 零(cls):
        核返回 cls(0)
    @staticmethod
    核定义 换(度):
        核返回 度 * 9 / 5 + 32
甲 = 温(20)
核说(甲.度, 温.零().度, 温.换(100))
甲.度 = 30
核说(甲.度)
""", """
class 温:
    甲 = 0
    def __init__(self, 度):
        self._度 = 度
    @property
    def 度(self):
        return self._度
    @度.setter
    def 度(self, v):
        self._度 = v
    @classmethod
    def 零(cls):
        return cls(0)
    @staticmethod
    def 换(度):
        return 度 * 9 / 5 + 32
甲 = 温(20)
print(甲.度, 温.零().度, 温.换(100))
甲.度 = 30
print(甲.度)
""")

加("推导式作用域", """
甲 = 5
乙 = [甲 核用 甲 遍历 核数列（3）]
核说(乙, 甲)
丙 = {i: i * 甲 核用 i 遍历 核数列（3）}
核说(丙)
丁 = {i % 2 核用 i 遍历 核数列（6）}
核说(sorted(丁))
""", """
甲 = 5
乙 = [甲 for 甲 in range(3)]
print(乙, 甲)
丙 = {i: i * 甲 for i in range(3)}
print(丙)
丁 = {i % 2 for i in range(6)}
print(sorted(丁))
""")

加("推导式带条件嵌套", """
核说([(i, j) 核用 i 遍历 核数列（4） 核若 i % 2 == 0 核用 j 遍历 核数列（3） 核若 j != i])
核说({i: j 核用 i 遍历 核数列（3） 核用 j 遍历 核数列（2） 核若 i > j})
""", """
print([(i, j) for i in range(4) if i % 2 == 0 for j in range(3) if j != i])
print({i: j for i in range(3) for j in range(2) if i > j})
""")

加("海象在推导式", """
核说([y 核用 x 遍历 核数列（6） 核若 (y := x * x) > 5])
""", """
print([y for x in range(6) if (y := x * x) > 5])
""")

加("增强赋值全家", """
甲 = 100
甲 //= 7
核说(甲)
甲 %= 4
核说(甲)
甲 **= 3
核说(甲)
甲 <<= 2
核说(甲)
甲 &= 12
核说(甲)
甲 |= 3
核说(甲)
甲 ^= 5
核说(甲)
甲 >>= 1
核说(甲)
乙 = [1]
乙 *= 3
核说(乙)
丙 = "a"
丙 += "b"
核说(丙)
""", """
甲 = 100
甲 //= 7
print(甲)
甲 %= 4
print(甲)
甲 **= 3
print(甲)
甲 <<= 2
print(甲)
甲 &= 12
print(甲)
甲 |= 3
print(甲)
甲 ^= 5
print(甲)
甲 >>= 1
print(甲)
乙 = [1]
乙 *= 3
print(乙)
丙 = "a"
丙 += "b"
print(丙)
""")

加("字面量前缀与下划线", """
核说(1_000_000, 0xFF_FF, 0o7_77, 0b1010_1010)
核说(1e-3, 2.5e2, 3j.imag)
核说(r"a\\nb", len(r"a\\nb"))
核说(b"\\xe4\\xbd\\xa0".decode("utf-8"))
核说(rb"x\\y")
""", """
print(1_000_000, 0xFF_FF, 0o7_77, 0b1010_1010)
print(1e-3, 2.5e2, 3j.imag)
print(r"a\\nb", len(r"a\\nb"))
print(b"\\xe4\\xbd\\xa0".decode("utf-8"))
print(rb"x\\y")
""")

加("匿名默认与闭包", """
甲 = [核匿名 x, n=i: x * n 核用 i 遍历 核数列（3）]
核说([f(2) 核用 f 遍历 甲])
乙 = 核匿名 *a, **k: (a, k)
核说(乙(1, 2, x=3))
""", """
甲 = [lambda x, n=i: x * n for i in range(3)]
print([f(2) for f in 甲])
乙 = lambda *a, **k: (a, k)
print(乙(1, 2, x=3))
""")

加("生成器表达式", """
核说(sum(i * i 核用 i 遍历 核数列（5）))
核说(max((i 核用 i 遍历 核数列（4）), default=-1))
核说(any(i > 2 核用 i 遍历 核数列（4）))
""", """
print(sum(i * i for i in range(5)))
print(max((i for i in range(4)), default=-1))
print(any(i > 2 for i in range(4)))
""")

加("星号转发", """
核定义 甲(*a, **k):
    核返回 (a, sorted(k.items()))
核定义 乙(*a, **k):
    核返回 甲(*a, **k)
核说(乙(1, 2, x=3, y=4))
丙 = [1, 2]
核说(甲(*丙, **{"z": 9}))
""", """
def 甲(*a, **k):
    return (a, sorted(k.items()))
def 乙(*a, **k):
    return 甲(*a, **k)
print(乙(1, 2, x=3, y=4))
丙 = [1, 2]
print(甲(*丙, **{"z": 9}))
""")

加("解包星号赋值", """
甲, *乙, 丙 = 核数列（6）
核说(甲, 乙, 丙)
*丁, = [1]
核说(丁)
[戊, 己] = (7, 8)
核说(戊, 己)
""", """
甲, *乙, 丙 = range(6)
print(甲, 乙, 丙)
*丁, = [1]
print(丁)
[戊, 己] = (7, 8)
print(戊, 己)
""")

加("全局跨函数", """
甲 = []
核定义 加(x):
    核全局 甲
    甲 = 甲 + [x]
核定义 换():
    核全局 甲
    甲 = []
加(1)
加(2)
核说(甲)
换()
核说(甲)
""", """
甲 = []
def 加(x):
    global 甲
    甲 = 甲 + [x]
def 换():
    global 甲
    甲 = []
加(1)
加(2)
print(甲)
换()
print(甲)
""")

加("类体作用域", """
核类 甲:
    x = 1
    y = [x 核用 _ 遍历 核数列（2）]
    核定义 说(self):
        核返回 self.x
核说(甲.y, 甲().说())
""", """
class 甲:
    x = 1
    y = [x for _ in range(2)]
    def 说(self):
        return self.x
print(甲.y, 甲().说())
""")

加("嵌套函数默认求值", """
甲 = 1
核定义 外():
    核定义 内(x=甲):
        核返回 x
    核返回 内
乙 = 外()
甲 = 99
核说(乙())
""", """
甲 = 1
def 外():
    def 内(x=甲):
        return x
    return 内
乙 = 外()
甲 = 99
print(乙())
""")

加("异常链与最终返回", """
核定义 甲():
    核试:
        核抛出 ValueError("里")
    核异常 ValueError 核作为 e:
        核抛出 KeyError("外") 核从 e
    核最终:
        核说("最终")
核试:
    甲()
核异常 KeyError 核作为 e:
    核说(str(e), type(e.__cause__).__name__)
""", """
def 甲():
    try:
        raise ValueError("里")
    except ValueError as e:
        raise KeyError("外") from e
    finally:
        print("最终")
try:
    甲()
except KeyError as e:
    print(str(e), type(e.__cause__).__name__)
""")

加("排序键与稳定性", """
甲 = [("b", 2), ("a", 2), ("c", 1)]
核说(sorted(甲, key=核匿名 t: t[1]))
核说(sorted(甲, key=核匿名 t: (-t[1], t[0])))
乙 = {"x": 3, "y": 1}
核说(sorted(乙, key=乙.get), sorted(乙.items(), key=核匿名 t: -t[1]))
""", """
甲 = [("b", 2), ("a", 2), ("c", 1)]
print(sorted(甲, key=lambda t: t[1]))
print(sorted(甲, key=lambda t: (-t[1], t[0])))
乙 = {"x": 3, "y": 1}
print(sorted(乙, key=乙.get), sorted(乙.items(), key=lambda t: -t[1]))
""")

加("f串嵌套格式", """
甲 = 3.14159
乙 = 7
核说(f"{甲:.2f}|{乙:>5d}|{乙:#x}|{甲:e}")
丙 = {"k": 1}
核说(f"{丙['k']=}")
核说(f"{乙!r:*>6}")
宽 = 8
核说(f"{甲:{宽}.3f}")
""", """
甲 = 3.14159
乙 = 7
print(f"{甲:.2f}|{乙:>5d}|{乙:#x}|{甲:e}")
丙 = {"k": 1}
print(f"{丙['k']=}")
print(f"{乙!r:*>6}")
宽 = 8
print(f"{甲:{宽}.3f}")
""")

加("百分号格式", """
核说("%s-%d-%.2f-%r" % ("甲", 3, 1.5, "乙"))
核说("%(名)s:%(岁)d" % {"名": "小核", "岁": 7})
核说("%5.2f|%-5d|%+d" % (1.5, 3, 4))
""", """
print("%s-%d-%.2f-%r" % ("甲", 3, 1.5, "乙"))
print("%(名)s:%(岁)d" % {"名": "小核", "岁": 7})
print("%5.2f|%-5d|%+d" % (1.5, 3, 4))
""")

加("字典视图与拷贝", """
甲 = {"a": [1], "b": 2}
乙 = 甲.copy()
乙["a"].append(2)
核说(甲, 乙)
核说(sorted(甲.keys()), sorted(甲.values(), key=str))
""", """
甲 = {"a": [1], "b": 2}
乙 = 甲.copy()
乙["a"].append(2)
print(甲, 乙)
print(sorted(甲.keys()), sorted(甲.values(), key=str))
""")

加("迭代器协议", """
核类 数:
    核定义 __init__(self, n):
        self.n = n
        self.i = 0
    核定义 __iter__(self):
        核返回 self
    核定义 __next__(self):
        核若 self.i >= self.n:
            核抛出 StopIteration
        self.i += 1
        核返回 self.i
核说(list(数(3)), sum(数(4)))
""", """
class 数:
    def __init__(self, n):
        self.n = n
        self.i = 0
    def __iter__(self):
        return self
    def __next__(self):
        if self.i >= self.n:
            raise StopIteration
        self.i += 1
        return self.i
print(list(数(3)), sum(数(4)))
""")

加("命名元组", """
核从 collections 核导入 namedtuple
点 = namedtuple("点", "x y")
甲 = 点(1, 2)
核说(甲.x, 甲.y, 甲, 甲._replace(x=9))
""", """
from collections import namedtuple
点 = namedtuple("点", "x y")
甲 = 点(1, 2)
print(甲.x, 甲.y, 甲, 甲._replace(x=9))
""")

加("正则中文", """
核导入 re
核说(re.findall(r"[\\u4e00-\\u9fff]+", "甲a乙b丙"))
核说(re.sub(r"\\d+", "#", "a1b22c333"))
核说(re.match(r"(\\w+)-(\\d+)", "甲-12").groups())
""", """
import re
print(re.findall(r"[\\u4e00-\\u9fff]+", "甲a乙b丙"))
print(re.sub(r"\\d+", "#", "a1b22c333"))
print(re.match(r"(\\w+)-(\\d+)", "甲-12").groups())
""")

加("异步生成器", """
核导入 asyncio
核异步 核定义 生(n):
    核用 i 遍历 核数列（n）:
        核等待 asyncio.sleep(0)
        核产出 i
核异步 核定义 主():
    出 = [x 核异步 核用 x 遍历 生(3)]
    核说(出)
asyncio.run(主())
""", """
import asyncio
async def 生(n):
    for i in range(n):
        await asyncio.sleep(0)
        yield i
async def 主():
    出 = [x async for x in 生(3)]
    print(出)
asyncio.run(主())
""")

加("三元嵌套与短路", """
核定义 甲(x):
    核返回 "小" 核若 x < 3 核否则 ("中" 核若 x < 7 核否则 "大")
核说([甲(i) 核用 i 遍历 (1, 5, 9)])
乙 = 核错 核和 (1 / 0)
核说(乙)
丙 = 核对 核或 (1 / 0)
核说(丙)
""", """
def 甲(x):
    return "小" if x < 3 else ("中" if x < 7 else "大")
print([甲(i) for i in (1, 5, 9)])
乙 = False and (1 / 0)
print(乙)
丙 = True or (1 / 0)
print(丙)
""")


def 异常类型(文):
    """从 stderr 里抠出最后一个异常类名，用来比较「两边是不是同一种错」。"""
    名们 = re.findall(r"([A-Za-z_][A-Za-z_0-9]*(?:Error|Exception|Iteration))", 文)
    return 名们[-1] if 名们 else ""


坏 = []
目录 = tempfile.mkdtemp(prefix="核语法差分_")
环 = dict(os.environ)
环["PYTHONIOENCODING"] = "utf-8"
环["PYTHONUTF8"] = "1"
for 名, 中文, 英文 in 用例:
    中路径 = os.path.join(目录, "甲.xht")
    英路径 = os.path.join(目录, "甲.py")
    with open(中路径, "w", encoding="utf-8", newline="\n") as f:
        f.write(中文.lstrip("\n"))
    with open(英路径, "w", encoding="utf-8", newline="\n") as f:
        f.write(英文.lstrip("\n"))
    r1 = subprocess.run([sys.executable, 核, 中路径], capture_output=True, env=环, timeout=60)
    r2 = subprocess.run([sys.executable, 英路径], capture_output=True, env=环, timeout=60)
    出1 = (r1.stdout or b"").decode("utf-8", "replace")
    出2 = (r2.stdout or b"").decode("utf-8", "replace")
    错1 = (r1.stderr or b"").decode("utf-8", "replace")
    if r1.returncode == r2.returncode == 0 and 出1 == 出2:
        print("  ok   %s" % 名)
    elif r1.returncode != 0 and r2.returncode != 0:
        # 两边都报错：只要异常类型一致就算语义相同
        # （比如类体里的推导式看不到类变量，Python 自己也是 NameError）
        甲型 = 异常类型(错1)
        乙型 = 异常类型((r2.stderr or b"").decode("utf-8", "replace"))
        if 甲型 and 甲型 == 乙型:
            print("  ok   %s（两边同样报 %s）" % (名, 甲型))
        else:
            坏.append(名)
            print("  !!   %s  核报 %r / 英报 %r" % (名, 甲型, 乙型))
    else:
        坏.append(名)
        print("  !!   %s" % 名)
        print("       核(%d)=%r" % (r1.returncode, 出1[:200]))
        print("       英(%d)=%r" % (r2.returncode, 出2[:200]))
        if 错1.strip():
            print("       核stderr: %s" % 错1.strip()[-400:])

print()
print("=" * 60)
print("语法差分：%d 例，%d 例不一致" % (len(用例), len(坏)))
if 坏:
    print("不一致：%s" % "、".join(坏))
    sys.exit(1)
print("语法差分全部一致")
