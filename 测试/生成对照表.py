# -*- coding: utf-8 -*-
"""生成《核语言 ↔ Python 对照表》，未定义的核语言留空待填。

对照表分四类：关键字 / 内置函数 / 方法 / 关键字参数。
每类都列出内核里已定义的映射，以及 Python 侧存在、但核语言还没定义的项
（这些行的「核语言」一栏留空，填好后补进 核.py 的对应表即可）。

用法：
    python 测试/生成对照表.py              输出到 对照表.md
    python 测试/生成对照表.py --xlsx       同时输出 Excel（需 openpyxl）
"""

import os
import sys

这里 = os.path.dirname(os.path.abspath(__file__))
根目录 = os.path.dirname(这里)
sys.path.insert(0, 根目录)

import 核  # noqa: E402

输出 = os.path.join(根目录, "对照表.md")

#: 需要覆盖的 Python 侧候选。核语言一栏留空的，就是还没定义的。
候选关键词 = """
False None True and as assert async await break class continue def del elif else
except finally for from global if import in is lambda nonlocal not or pass raise
return try while with yield
""".split()

候选函数 = """
abs all any ascii bin bool bytearray bytes callable chr classmethod compile complex
delattr dict dir divmod enumerate eval exec filter float format frozenset getattr
globals hasattr hash help hex id input int isinstance issubclass iter len list
locals map max memoryview min next object oct open ord pow print property range
repr reversed round set setattr slice sorted staticmethod str sum super tuple type
vars zip
""".split()

候选方法 = """
append clear copy count extend index insert pop remove reverse sort
capitalize casefold center endswith expandtabs find format isalnum isalpha
isascii isdecimal isdigit isidentifier islower isnumeric isprintable isspace
istitle isupper join ljust lower lstrip partition replace rfind rindex rjust
rpartition rsplit rstrip split splitlines startswith strip swapcase title
translate upper zfill
add difference difference_update discard intersection intersection_update
isdisjoint issubset issuperset symmetric_difference symmetric_difference_update
union update
get items keys values setdefault popitem fromkeys
read readline readlines write writelines close seek tell flush
""".split()

候选参数 = "end sep file flush key reverse".split()

#: 这些英文已有中文写法（反向索引），用于在表里标出「已定义」
函数反查 = {v: k for k, v in 核.函数表.items()}
方法反查 = {v: k for k, v in 核.方法表.items()}
参数反查 = {v: k for k, v in 核.参数表.items()}
关键词反查 = {v: k for k, v in 核.关键词表.items()}


def _行(中文, 英文, 说明=""):
    return "| `%s` | `%s` | %s |" % (中文 or "", 英文, 说明)


def 生成():
    行集 = []
    添加 = 行集.append

    添加("# 核语言 ↔ Python 对照表")
    添加("")
    添加("> **「核语言」一栏留空的，就是还没定义的写法**，想好中文名后填进空格即可。")
    添加("> 填完把对应关系补进 `核.py` 的 `关键词表` / `函数表` / `方法表` / `参数表`，")
    添加("> 再运行 `python 测试/自检对照表.py` 验证有无重名。")
    添加("")
    添加("本表由 `python 测试/生成对照表.py` 自动生成，数据取自 `核.py`。")
    添加("")
    添加("## 怎么填")
    添加("")
    添加("1. 在「核语言」栏写下中文名，例如把空着的 `sum` 填成 `核求和`")
    添加("2. 把这一行补进 `核.py` 对应的表（`函数表` / `方法表` / …）")
    添加("3. 运行 `python 测试/自检对照表.py` 检查有没有重名或冲突")
    添加("4. 再运行 `python 测试/生成对照表.py` 刷新本表")
    添加("")
    添加("**命名惯例**（照现有风格起名，读起来才统一）：")
    添加("")
    添加("| 类别 | 前缀 | 现有例子 |")
    添加("| --- | --- | --- |")
    添加("| 关键字 | `核` | `核若` `核定义` `核返回` |")
    添加("| 内置函数 | `核` / `说核` | `核长度` `核最大` `说核` |")
    添加("| 方法 | `核` | `核加入` `核排序` `木亥` |")
    添加("| 关键字参数 | `核` | `核尾` `核隔` |")
    添加("")
    添加("> 注意：方法只在 `.` 之后生效，所以方法名可以与函数名重复；")
    添加("> 关键字不能与已有中文名重复，否则自检会报错。")
    添加("")

    统计 = {}

    # —— 一、关键字 ——
    添加("## 一、关键字")
    添加("")
    添加("| 核语言 | Python | 备注 |")
    添加("| --- | --- | --- |")
    已定义关键 = set(核.关键词表.values())
    未定义关键 = []
    for 英 in 候选关键词:
        中 = 关键词反查.get(英)
        if 中:
            添加(_行(中, 英))
        else:
            未定义关键.append(英)
            # 规则表里明确要求保留英文的，标一下
            添加(_行("", 英, "待定义"))
    统计["关键字"] = (len(已定义关键 & set(候选关键词)), len(未定义关键))
    添加("")

    # —— 二、内置函数 ——
    添加("## 二、内置函数")
    添加("")
    添加("| 核语言 | Python | 备注 |")
    添加("| --- | --- | --- |")
    未定义函数 = []
    for 英 in 候选函数:
        中 = 函数反查.get(英)
        if 中:
            添加(_行(中, 英))
        else:
            未定义函数.append(英)
            添加(_行("", 英, "待定义"))
    统计["内置函数"] = (
        len(set(核.函数表.values()) & set(候选函数)),
        len(未定义函数),
    )
    添加("")

    # —— 三、方法 ——
    添加("## 三、方法")
    添加("")
    添加("方法只在 `.` 之后生效，例如 `句子.木亥（\",\"）`。")
    添加("")
    添加("| 核语言 | Python | 备注 |")
    添加("| --- | --- | --- |")
    未定义方法 = []
    for 英 in 候选方法:
        中 = 方法反查.get(英)
        if 中:
            添加(_行(中, 英))
        else:
            未定义方法.append(英)
            添加(_行("", 英, "待定义"))
    统计["方法"] = (len(set(核.方法表.values()) & set(候选方法)), len(未定义方法))
    添加("")

    # —— 四、关键字参数 ——
    添加("## 四、关键字参数")
    添加("")
    添加("关键字参数只在 `名字=` 位置生效，例如 `核说（…, 核尾=\"\"）`。")
    添加("")
    添加("| 核语言 | Python | 备注 |")
    添加("| --- | --- | --- |")
    未定义参数 = []
    for 英 in 候选参数:
        中 = 参数反查.get(英)
        if 中:
            添加(_行(中, 英))
        else:
            未定义参数.append(英)
            添加(_行("", 英, "待定义"))
    统计["关键字参数"] = (len(set(核.参数表.values()) & set(候选参数)), len(未定义参数))
    添加("")

    # —— 五、语法结构（非一对一，人工说明）——
    添加("## 五、语法结构")
    添加("")
    添加("这些不是「一个词换一个词」，而是整句的写法。")
    添加("")
    添加("| 核语言 | Python | 备注 |")
    添加("| --- | --- | --- |")
    添加("| `核用 i 遍历 x：` | `for i in x:` | 循环 |")
    添加("| `核若 条件：` | `if 条件:` | 条件 |")
    添加("| `又核若 条件：` | `elif 条件:` | 否则若 |")
    添加("| `核否则：` | `else:` | 否则 |")
    添加("| `核循环若 条件：` | `while 条件:` | 当型循环 |")
    添加("| `核定义 名（参数）：` | `def 名(参数):` | 函数定义 |")
    添加("| `核返回 值` | `return 值` | 返回 |")
    添加("| `核删 名` | `del 名` | 删除 |")
    添加("| `核核 注释` | `# 注释` | 注释 |")
    添加('| `核"…{x:.2f}"` | `f"…{x:.2f}"` | f 字符串 |')
    添加("| `核说（…, 核尾=\"\"）` | `print(…, end=\"\")` | 不换行 |")
    添加("| `核说（…, 核隔=\"-\"）` | `print(…, sep=\"-\")` | 自定义分隔符 |")
    添加("")

    # —— 六、汇总 ——
    添加("## 六、待定义统计")
    添加("")
    添加("| 类别 | 已定义 | 待定义 |")
    添加("| --- | --- | --- |")
    合计已 = 合计未 = 0
    for 类, (已, 未) in 统计.items():
        添加("| %s | %d | %d |" % (类, 已, 未))
        合计已 += 已
        合计未 += 未
    添加("| **合计** | **%d** | **%d** |" % (合计已, 合计未))
    添加("")

    return "\n".join(行集) + "\n", 统计


def 主():
    文本, 统计 = 生成()
    with open(输出, "w", encoding="utf-8", newline="\n") as f:
        f.write(文本)
    print("已生成：%s" % 输出)
    print()
    print("待定义的写法：")
    for 类, (已, 未) in 统计.items():
        print("  %-8s 已定义 %2d，待定义 %2d" % (类, 已, 未))

    if "--xlsx" in sys.argv:
        try:
            导出表格(文本)
        except ImportError:
            print("\n（未安装 openpyxl，跳过 Excel 导出）")
    return 0


def 导出表格(文本):
    """把 markdown 表格另存为 Excel，方便直接填。"""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    工作簿 = Workbook()
    表 = 工作簿.active
    表.title = "对照表"
    表.append(["类别", "核语言", "Python", "备注"])

    当前类 = ""
    for 行 in 文本.splitlines():
        if 行.startswith("## "):
            当前类 = 行[3:].strip()
            continue
        if not 行.startswith("| `"):
            continue
        格 = [c.strip().strip("`") for c in 行.strip("|").split("|")]
        if len(格) < 2:
            continue
        中文 = 格[0] if 格[0] else ""
        英文 = 格[1]
        说明 = 格[2] if len(格) > 2 else ""
        表.append([当前类, 中文, 英文, 说明])

    表.column_dimensions["A"].width = 14
    表.column_dimensions["B"].width = 16
    表.column_dimensions["C"].width = 22
    表.column_dimensions["D"].width = 16
    for 单元格 in 表[1]:
        单元格.font = Font(bold=True, color="FFFFFF")
        单元格.fill = PatternFill("solid", fgColor="4472C4")
    待填 = PatternFill("solid", fgColor="FFF2CC")
    for 行 in 表.iter_rows(min_row=2):
        行[1].alignment = Alignment(horizontal="left")
        if not 行[1].value:
            行[1].fill = 待填

    xlsx = os.path.join(根目录, "对照表.xlsx")
    工作簿.save(xlsx)
    print("\n已导出 Excel：%s（浅黄格＝待定义）" % xlsx)


if __name__ == "__main__":
    sys.exit(主())
