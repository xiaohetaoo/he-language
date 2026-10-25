#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""核语言（第一版）

把 .xht 源文件转译成 Python 3 源码后执行，只用标准库。

设计要点
--------
1. 转译保证行号不变，运行时报错的行号与 .xht 源文件一致。
2. 中英文符号视同：代码区的全角标点自动归一，字符串与注释内容保持原样。
3. 源码里出现、但对照表没有定义的英文写法，原样交给 Python 执行，
   同时记入 未定义.txt（跨运行累积去重），方便后续扩展语言。

用法见 `核 帮助`。
"""

import codeop
import os
import re
import sys
import time
import traceback
import unicodedata

#: 当前版本号。每次发布递增，并把整套源码归档到 版本/ 目录（见 版本记录.md）。
版本 = "0.0.11"
程序名 = "核语言"

扩展名 = ".xht"

# ---------------------------------------------------------------------------
# 一、对照表
# ---------------------------------------------------------------------------

#: 语句关键字。标「补」的是规则表之外、为了让第一版可写而补齐的。
关键词表 = {
    # —— 规则表原有 ——
    "核若": "if",
    "又核若": "elif",
    "核否则": "else",
    "核用": "for",
    "遍历": "in",
    "核循环若": "while",
    "核定义": "def",
    "核返回": "return",
    "核删": "del",
    "核否": "not",
    "核和": "and",
    "核或": "or",
    "核对": "True",
    "核错": "False",
    # —— 补 ——
    "核空": "None",
    "核断开": "break",
    "核跳过": "continue",
    "核略过": "pass",
    "核是": "is",
    "核在": "in",
    "核导入": "import",
    "核从": "from",
    "核作为": "as",
    "核类": "class",
    "核试": "try",
    "核异常": "except",
    "核最终": "finally",
    "核抛出": "raise",
    "核断言": "assert",
    "核全局": "global",
    "核非局部": "nonlocal",
    "核带": "with",
    "核产出": "yield",
    "核匿名": "lambda",
    "核异步": "async",
    "核等待": "await",
}

#: 内置函数。
函数表 = {
    # —— 规则表原有 ——
    "说核": "input",
    "核说": "print",
    "核整数": "int",
    "核实数": "float",
    "核字符": "str",
    "核列表": "list",
    "核字典": "dict",
    "核集合": "set",
    "核长度": "len",
    "核最小": "min",
    "核最大": "max",
    "核排好": "sorted",
    "核绝对值": "abs",
    "核数列": "range",
    "核取舍": "round",
    # —— 用户已定名 ——
    "核布尔": "bool",
    "核帮助": "help",
    "核求和": "sum",
    # —— 第二批（按命名规律补） ——
    "核全": "all",
    "核有": "any",
    "核二进": "bin",
    "核可调": "callable",
    "核字符号": "chr",
    "核复数": "complex",
    "核删属": "delattr",
    "核列属": "dir",
    "核除余": "divmod",
    "核编号": "enumerate",
    "核求值": "eval",
    "核格化": "format",
    "核执行": "exec",
    "核筛选": "filter",
    "核冻结集": "frozenset",
    "核取属": "getattr",
    "核全局表": "globals",
    "核有属": "hasattr",
    "核哈希": "hash",
    "核十六": "hex",
    "核编号值": "id",
    "核是类": "isinstance",
    "核是子类": "issubclass",
    "核迭代": "iter",
    "核局部表": "locals",
    "核映射": "map",
    "核下一个": "next",
    "核对象": "object",
    "核八进": "oct",
    "核打开": "open",
    "核码位": "ord",
    "核乘方": "pow",
    "核表示": "repr",
    "核反排": "reversed",
    "核设属": "setattr",
    "核切片": "slice",
    "核父类": "super",
    "核元组": "tuple",
    "核类型": "type",
    "核变量表": "vars",
    "核拉链": "zip",
}

#: 方法名，只在 `.` 之后生效。
方法表 = {
    # —— 规则表原有 ——
    "木亥": "split",
    "核排序": "sort",
    "核加入": "append",
    "核找": "find",
    "核数": "count",
    "核换": "replace",
    # —— 补 ——
    "核去除": "strip",
    "核去左": "lstrip",
    "核去右": "rstrip",
    "核取": "get",
    "核键": "keys",
    "核值": "values",
    "核项": "items",
    "核弹出": "pop",
    "核上": "upper",
    "核下": "lower",
    "核插入": "insert",
    "核倒序": "reverse",
    "核扩展": "extend",
    "核开头": "startswith",
    "核结尾": "endswith",
    "核连接": "join",
    "核复制": "copy",
    "核更新": "update",
    "核格式": "format",
    "核转列表": "splitlines",
    # —— 第二批（按命名规律补） ——
    "核添加": "add",
    "核首大写": "capitalize",
    "核居中": "center",
    "核清空": "clear",
    "核关闭": "close",
    "核差集": "difference",
    "核差集更新": "difference_update",
    "核舍弃": "discard",
    "核展制表": "expandtabs",
    "核即刷": "flush",
    "核建字典": "fromkeys",
    "核位序": "index",
    "核交集": "intersection",
    "核交集更新": "intersection_update",
    "核是字数值": "isalnum",
    "核是字母": "isalpha",
    "核是十进制串": "isdecimal",
    "核是数字": "isdigit",
    "核不相交": "isdisjoint",
    "核是标识符": "isidentifier",
    "核是小写": "islower",
    "核是数值": "isnumeric",
    "核可打印": "isprintable",
    "核是空白": "isspace",
    "核是子集": "issubset",
    "核是超集": "issuperset",
    "核是标题式": "istitle",
    "核是大写": "isupper",
    "核左齐": "ljust",
    "核三分": "partition",
    "核弹项": "popitem",
    "核读取": "read",
    "核读行": "readline",
    "核读多行": "readlines",
    "核移除": "remove",
    "核右找": "rfind",
    "核右位序": "rindex",
    "核右齐": "rjust",
    "核右三分": "rpartition",
    "核右木亥": "rsplit",
    "核定位": "seek",
    "核取默认": "setdefault",
    "核换大小": "swapcase",
    "核对称差": "symmetric_difference",
    "核对称差更新": "symmetric_difference_update",
    "核位置": "tell",
    "核标题式": "title",
    "核翻译": "translate",
    "核并集": "union",
    "核写入": "write",
    "核写多行": "writelines",
    "核补零": "zfill",
}

#: 关键字参数名，只在 `名字=` 位置生效。
参数表 = {
    "核尾": "end",
    "核隔": "sep",
    "核文件": "file",
    "核键序": "key",
    # 与方法表里的 flush(核即刷)/reverse(核倒序) 是不同位置上的同名参数：
    # 参数只在 `名字=` 处生效，方法只在 `.` 之后生效，互不干扰。
    "核刷新": "flush",
    "核反序": "reverse",
}

#: 常见英文关键字参数；出现在 `名字=` 位置且没定义时也要记一笔。
英文参数 = {"end", "sep", "file", "flush", "key", "reverse"}

#: 字符串前缀：核"..." 等价于 f"..."
字符串前缀 = "核"

# —— 英文侧清单：用于「中英都认」和识别未定义写法 ——

英文关键词 = set("""
False None True and as assert async await break class continue def del elif else
except finally for from global if import in is lambda nonlocal not or pass raise
return try while with yield
""".split())

英文内置 = set("""
abs aiter all anext any ascii bin bool breakpoint bytearray bytes callable chr
classmethod compile complex delattr dict dir divmod enumerate eval exec filter
float format frozenset getattr globals hasattr hash help hex id input int
isinstance issubclass iter len list locals map max memoryview min next object oct
open ord pow print property range repr reversed round set setattr slice sorted
staticmethod str sum super tuple type vars zip __import__
""".split())

英文方法 = set("""
append clear copy count extend index insert pop remove reverse sort
capitalize casefold center endswith expandtabs find format format_map isalnum
isalpha isascii isdecimal isdigit isidentifier islower isnumeric isprintable
isspace istitle isupper join ljust lower lstrip partition replace rfind rindex
rjust rpartition rsplit rstrip split splitlines startswith strip swapcase title
translate upper zfill
add difference difference_update discard intersection intersection_update
isdisjoint issubset issuperset symmetric_difference symmetric_difference_update
union update
get items keys values setdefault popitem fromkeys
read readline readlines write writelines close seek tell flush
""".split())

已定义英文函数 = set(函数表.values()) | set(关键词表.values())
已定义英文方法 = set(方法表.values())
已定义英文参数 = set(参数表.values())

#: 异常类型名。写 `核异常 除零错误：` 时转成 `except ZeroDivisionError:`。
#: 这些名字只在 `核异常` / `核抛出` 之后生效，别处仍按普通标识符处理。
异常表 = {
    "错误": "Exception",
    "常见错误": "Exception",
    "除零错误": "ZeroDivisionError",
    "零除错误": "ZeroDivisionError",
    "类型错误": "TypeError",
    "值错误": "ValueError",
    "下标错误": "IndexError",
    "越界错误": "IndexError",
    "键错误": "KeyError",
    "名字错误": "NameError",
    "属性错误": "AttributeError",
    "断言错误": "AssertionError",
    "断词错误": "StopIteration",
    "迭代结束": "StopIteration",
    "文件找不到": "FileNotFoundError",
    "文件错误": "FileNotFoundError",
    "系统错误": "OSError",
    "缩进错误": "IndentationError",
    "制表符错误": "TabError",
    "递归太深": "RecursionError",
    "模块找不到": "ModuleNotFoundError",
    "语法错误": "SyntaxError",
    "未绑定错误": "UnboundLocalError",
}

#: 常见异常的中文提示。
异常说明 = {
    "NameError": "用到了没定义的变量或函数，检查名字是否写错",
    "UnboundLocalError": "变量在赋值前就被使用了",
    "ZeroDivisionError": "除数不能为 0",
    "TypeError": "类型不匹配，检查参与运算的值",
    "ValueError": "类型对，但内容不合法",
    "IndexError": "下标超出范围",
    "KeyError": "字典里没有这个键",
    "AttributeError": "对象没有这个属性或方法",
    "FileNotFoundError": "找不到文件",
    "RecursionError": "递归太深",
    "ModuleNotFoundError": "找不到模块。.xht 模块要和主脚本放在同一目录；Python 库第一版不引入",
    "IndentationError": "缩进不对，检查每行开头的空格",
    "TabError": "缩进里混用了空格和制表符",
    "SyntaxError": "语法不对",
    "StopIteration": "迭代已经结束",
    "AssertionError": "断言失败",
    "OSError": "文件或系统调用出错",
}


# ---------------------------------------------------------------------------
# 二、基础工具
# ---------------------------------------------------------------------------


#: NFKC 不会改写的中文引号，额外映射成普通引号（只在代码区生效）。
引号别名 = {
    "\u201c": '"',  # 左双引号 “
    "\u201d": '"',  # 右双引号 ”
    "\u2018": "'",  # 左单引号 ‘
    "\u2019": "'",  # 右单引号 ’
    "\u300c": '"',  # 「
    "\u300d": '"',  # 」
    "\u300e": '"',  # 『
    "\u300f": '"',  # 』
}


def 规范化单字(c):
    """单字符 NFKC 归一；长度变化（罕见）时保持原样。"""
    if ord(c) < 128:
        return c
    别名 = 引号别名.get(c)
    if 别名 is not None:
        return 别名
    n = unicodedata.normalize("NFKC", c)
    return n if len(n) == 1 else c


def 是标识符字符(c):
    return c == "_" or c.isalnum() or (ord(c) > 127 and c.isidentifier())


def 词左界(s, i):
    return i <= 0 or not 是标识符字符(s[i - 1])


def 词右界(s, i):
    return i >= len(s) or not 是标识符字符(s[i])


def 规范化源码(s):
    """代码区全角→半角；字符串内容与注释内容保持原样。"""
    结果 = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c == "\n":
            结果.append(c)
            i += 1
            continue
        if c == "#":
            j = s.find("\n", i)
            j = n if j < 0 else j
            结果.append(s[i:j])
            i = j
            continue
        if s.startswith("核核", i) and 词左界(s, i) and 词右界(s, i + 2):
            j = s.find("\n", i)
            j = n if j < 0 else j
            结果.append(s[i:j])
            i = j
            continue

        nc = 规范化单字(c)
        if nc in ("'", '"'):
            引号 = nc
            if i + 2 < n and 规范化单字(s[i + 1]) == nc and 规范化单字(s[i + 2]) == nc:
                引号 = nc * 3
            # 关键：收尾只看「原字符」是否与起始引号相同，或者是否属于
            # 与之对应的那一对中文别名。
            # 之前用 规范化单字(s[k]) 判断，而 NFKC/别名会把 「」『』 都归一成
            # 普通的 "，于是字符串内容里的「」被当成结束符，内容被悄悄改写
            # —— 与「字符串内容保持原样」的承诺相违。
            if c in ("\u201c", "\u300c", "\u300e"):
                收尾集 = {"\u201d", "\u300d", "\u300f"}
            elif c in ("\u201d", "\u300d", "\u300f"):
                收尾集 = {"\u201d", "\u300d", "\u300f"}
            elif c in ("\u2018",):
                收尾集 = {"\u2019"}
            elif c in ("\u2019",):
                收尾集 = {"\u2019"}
            else:
                收尾集 = {c}
            结果.append(引号)
            k = i + len(引号)
            内容起 = k
            while k < n:
                if s[k] == "\\":
                    k += 2
                    continue
                if len(引号) == 1:
                    if s[k] in 收尾集:
                        break
                elif (
                    k + 2 < n
                    and s[k] == 引号[0]
                    and s[k + 1] == 引号[0]
                    and s[k + 2] == 引号[0]
                ):
                    break
                k += 1
            结果.append(s[内容起:k])
            if k < n:
                结果.append(引号)
                k += len(引号)
            i = k
            continue

        结果.append(nc)
        i += 1
    return "".join(结果)


# ---------------------------------------------------------------------------
# 三、未定义清单
# ---------------------------------------------------------------------------

未定义文件名 = "未定义.txt"

报告头 = [
    "# 核语言 未定义清单",
    "# 说明：下面这些写法出现在源码里，但核语言对照表还没有定义，",
    "#       已按原样交给 Python 执行。把它们补进对照表，就能用中文写。",
    "# 格式：写法 <TAB> 类别 <TAB> 出现次数 <TAB> 首次位置 <TAB> 最近位置",
]

类别序 = {"关键字": 0, "内置函数": 1, "方法": 2, "参数名": 3}


class 未定义报告:
    """跨运行累积的未定义写法记录。"""

    def __init__(self, 路径):
        self.路径 = 路径
        self.条目 = {}
        self.读取()

    def 读取(self):
        if not self.路径 or not os.path.exists(self.路径):
            return
        try:
            with open(self.路径, "r", encoding="utf-8") as f:
                行集 = f.readlines()
        except OSError:
            return
        for 行 in 行集:
            行 = 行.rstrip("\r\n")
            if not 行 or 行.startswith("#"):
                continue
            部分 = 行.split("\t")
            if len(部分) < 5:
                continue
            写法, 类别, 次数, 首次, 最近 = 部分[:5]
            try:
                次数 = int(次数)
            except ValueError:
                次数 = 1
            self.条目[(写法, 类别)] = {"次数": 次数, "首次": 首次, "最近": 最近}

    def 记录(self, 写法, 类别, 文件, 行, 列):
        位置 = "%s:%d:%d" % (self._相对(文件), 行, 列)
        key = (写法, 类别)
        e = self.条目.get(key)
        if e is None:
            self.条目[key] = {"次数": 1, "首次": 位置, "最近": 位置}
        else:
            e["次数"] += 1
            e["最近"] = 位置

    def _相对(self, 文件):
        """位置尽量写成相对清单所在目录的路径，清单更好读。"""
        if not self.路径 or not 文件:
            return 文件
        基准 = os.path.dirname(os.path.abspath(self.路径))
        try:
            相对 = os.path.relpath(os.path.abspath(文件), 基准)
        except (ValueError, OSError):
            return 文件
        return 相对.replace("\\", "/")

    def 条数(self):
        return len(self.条目)

    def 保存(self):
        if not self.路径:
            return
        行集 = list(报告头)
        行集.append("# 最近更新：%s" % time.strftime("%Y-%m-%d %H:%M:%S"))
        行集.append("")
        for key in sorted(self.条目, key=lambda k: (类别序.get(k[1], 9), k[0])):
            e = self.条目[key]
            行集.append(
                "%s\t%s\t%d\t%s\t%s" % (key[0], key[1], e["次数"], e["首次"], e["最近"])
            )
        try:
            目录 = os.path.dirname(os.path.abspath(self.路径))
            if 目录 and not os.path.isdir(目录):
                os.makedirs(目录, exist_ok=True)
            with open(self.路径, "w", encoding="utf-8", newline="\n") as f:
                f.write("\n".join(行集) + "\n")
        except OSError:
            pass


def 默认报告路径(源文件=None):
    """未定义清单放在哪儿。

    规则：**源文件所在目录**，一个项目一份。
    以前这个函数收了「源文件」参数却完全没用，永远写到 os.getcwd() ——
    于是从别的目录运行 `核 运行 D:\\项目\\a.xht` 时，清单会掉到
    进程当前目录，而不是项目目录；而且「核 报告 D:\\项目\\a.xht」
    查的是源文件目录下的清单，和实际写出的位置对不上。
    """
    if 源文件:
        目录 = os.path.dirname(os.path.abspath(源文件))
        if 目录:
            return os.path.join(目录, 未定义文件名)
    return os.path.abspath(os.path.join(os.getcwd(), 未定义文件名))


# ---------------------------------------------------------------------------
# 四、转译器
# ---------------------------------------------------------------------------

_字符串起点 = re.compile(r"(?:(?P<py>[rRbBuUfF]{1,2})|(?P<he>核))?(?P<q>'''|\"\"\"|'|\")")

_数字 = re.compile(
    r"""
    (?:
        0[xX][0-9a-fA-F_]+
      | 0[bB][01_]+
      | 0[oO][0-7_]+
      | (?:\d[\d_]*)?\.\d[\d_]*(?:[eE][+-]?\d+)?
      | \d[\d_]*(?:\.(?!\.)[\d_]*)?(?:[eE][+-]?\d+)?
    )
    """,
    re.X,
)

def _找引号结束(s, j, 引号):
    k, n = j, len(s)
    while k < n:
        if s[k] == "\\":
            k += 2
            continue
        if s.startswith(引号, k):
            return k
        k += 1
    return n


def 字符串区间(s):
    """找出 s 里所有字符串字面量的区间 [(起, 止), …]。

    供编辑器的语法高亮用 —— 高亮必须知道哪些字符在字符串里，
    否则会把字符串内容误当成注释/关键字染色。
    这里和转译器用同一套前缀与引号规则，保证两边说同样的话。
    """
    区间 = []
    i, n = 0, len(s)
    while i < n:
        m = _字符串起点.match(s, i)
        if not m:
            i += 1
            continue
        # 前缀后面必须不是标识符字符（否则 x'abc' 里的 abc 不是字符串）
        前缀 = m.group("py") or m.group("he")
        if 前缀 and i > 0 and 是标识符字符(s[i - 1]):
            i += 1
            continue
        引号 = m.group("q")
        内容起 = m.end()
        结束 = _找引号结束(s, 内容起, 引号)
        止 = min(结束 + len(引号), n)
        区间.append((i, 止))
        i = 止 if 止 > i else i + 1
    return 区间


def _找字段结束(s, i):
    """s[i] == '{'，返回配对的 '}'；失败返回 -1。"""
    深度 = 0
    k, n = i + 1, len(s)
    while k < n:
        c = s[k]
        if c in ("'", '"'):
            引号 = c
            if s.startswith(c * 3, k):
                引号 = c * 3
            k += len(引号)
            while k < n:
                if s[k] == "\\":
                    k += 2
                    continue
                if s.startswith(引号, k):
                    k += len(引号)
                    break
                k += 1
            continue
        if c in "([{":
            深度 += 1
        elif c in ")}]":
            if c == "}" and 深度 == 0:
                return k
            深度 -= 1
        k += 1
    return -1


def _切分字段(字段):
    """把 f-string 花括号内容切成「表达式」和「!转换:格式」两段。"""
    深度 = 0
    for k, c in enumerate(字段):
        if c in "([{":
            深度 += 1
        elif c in ")]}":
            深度 -= 1
        elif 深度 == 0 and c in "!:":
            return 字段[:k], 字段[k:]
    return 字段, ""


class 转译器:
    def __init__(self, 文件名="<源码>", 报告=None, 行=1, 列=1):
        self.文件名 = 文件名
        self.报告 = 报告
        self.行 = 行
        self.列 = 列
        self.输出 = []
        self.括号 = []
        self.上一个是点 = False
        self.已记 = set()
        self._新位置 = 0

    # —— 输出与位置 ——

    def 写(self, 文本):
        self.输出.append(文本)

    def 前进(self, 片段):
        for ch in 片段:
            if ch == "\n":
                self.行 += 1
                self.列 = 1
            else:
                self.列 += 1

    def 记录(self, 写法, 类别, 行, 列):
        """记录一次未定义写法。

        每次都计数（这样「出现次数」是真实的），但首次位置保持不变；
        `已记` 只用来避免同一次转译里同一位置被重复记（f-string 会递归转译）。
        """
        if self.报告 is None:
            return
        key = (写法, 类别, 行, 列)
        if key in self.已记:
            return
        self.已记.add(key)
        self.报告.记录(写法, 类别, self.文件名, 行, 列)

    # —— 入口 ——

    def 转译(self, s):
        self.扫描(s)
        return "".join(self.输出)

    def 扫描(self, s):
        i, n = 0, len(s)
        while i < n:
            c = s[i]

            if c == "\n":
                self.写("\n")
                self.前进("\n")
                self.上一个是点 = False
                i += 1
                continue

            if c == "\\" and i + 1 < n and s[i + 1] == "\n":
                self.写("\\\n")
                self.前进("\\\n")
                i += 2
                continue

            if c in " \t\r":
                self.写(c)
                self.前进(c)
                i += 1
                continue

            if c == "#":
                j = s.find("\n", i)
                j = n if j < 0 else j
                self.写(s[i:j])
                self.前进(s[i:j])
                i = j
                continue

            if s.startswith("核核", i) and 词左界(s, i) and 词右界(s, i + 2):
                j = s.find("\n", i)
                j = n if j < 0 else j
                内容 = s[i + 2:j]
                if not 内容:
                    self.写("#")
                elif 内容[:1].isspace():
                    self.写("# " + 内容.lstrip())
                else:
                    self.写("#" + 内容)
                self.前进(s[i:j])
                i = j
                continue

            if c == '"' or c == "'" or c in "核rRbBuUfF":
                if self.尝试字符串(s, i):
                    i = self._新位置
                    continue

            if c.isidentifier() or c == "_":
                j = i
                buf = []
                while j < n:
                    cj = s[j]
                    if cj == "_" or cj.isalnum() or cj.isidentifier():
                        buf.append(cj)
                        j += 1
                    else:
                        break
                if not buf:
                    self.写(c)
                    self.前进(c)
                    i += 1
                    continue
                名字 = "".join(buf)
                是参数 = (
                    bool(self.括号)
                    and 词左界(s, i)
                    and self._前一个有效字符(s, i) in "(,"
                    and self._后面是等号(s, j)
                )
                译 = self.翻译标识符(名字, self.行, self.列, 是参数, s, i, j)
                self.写(译)
                self.前进(s[i:j])
                self.上一个是点 = False
                i = j
                continue

            if c.isdigit() or (
                c == "." and not self.上一个是点 and i + 1 < n and s[i + 1].isdigit()
            ):
                m = _数字.match(s, i)
                if m:
                    self.写(m.group(0))
                    self.前进(m.group(0))
                    i = m.end()
                    self.上一个是点 = False
                    continue

            if c == ".":
                self.写(".")
                self.前进(".")
                self.上一个是点 = True
                i += 1
                continue

            if c in "([{":
                self.括号.append(c)
            elif c in ")]}":
                if self.括号:
                    self.括号.pop()

            self.写(c)
            self.前进(c)
            self.上一个是点 = False
            i += 1

    # —— 上下文小工具 ——

    @staticmethod
    def _前一个有效字符(s, i):
        k = i - 1
        while k >= 0 and s[k] in " \t\r":
            k -= 1
        return s[k] if k >= 0 else ""

    @staticmethod
    def _后面是等号(s, j):
        k = j
        while k < len(s) and s[k] in " \t\r":
            k += 1
        return k < len(s) and s[k] == "=" and not s.startswith("==", k) and not s.startswith("=>", k)

    def _在赋值左边(self, s, i, j):
        """判断这个标识符是否处在语句开头、且后面紧跟 = 号（即定义新名字）。"""
        行首 = s.rfind("\n", 0, i) + 1
        前缀 = s[行首:i]
        if 前缀.strip() and not 前缀.strip().isidentifier():
            return False
        return self._后面是等号(s, j)

    def _在异常位置(self, s, i):
        """判断这个标识符是否是「核异常 …」或「核抛出 …」的类型名。

        只认紧跟在引导词之后的那一个名字：
        `核异常 除零错误 核作为 错误：` 里的 除零错误 是类型，错误 是变量名。
        """
        行首 = s.rfind("\n", 0, i) + 1
        前缀 = s[行首:i]
        引导位置 = -1
        引导词 = ""
        for 引导 in ("核异常", "核抛出"):
            位置 = 前缀.rfind(引导)
            if 位置 > 引导位置:
                引导位置 = 位置
                引导词 = 引导
        if 引导位置 < 0:
            return False
        之后 = 前缀[引导位置 + len(引导词):]
        # 走到「核作为」之后，就说明已经在变量名位置了，不再是类型
        if "核作为" in 之后:
            return False
        # 多个异常并列时（逗号之后）也都算类型，这里不做限制；
        # 但若这段里已经有别的标识符（说明当前不是第一个），也照常允许。
        return True

    # —— 标识符 ——

    def 翻译标识符(self, 名字, 行, 列, 是参数, s, i, j):
        if self.上一个是点:
            if 名字 in 方法表:
                return 方法表[名字]
            if 名字 in 英文方法 and 名字 not in 已定义英文方法:
                self.记录(名字, "方法", 行, 列)
            return 名字

        if 是参数:
            if 名字 in 参数表:
                return 参数表[名字]
            if 名字 in 英文参数 and 名字 not in 已定义英文参数:
                self.记录(名字, "参数名", 行, 列)
            return 名字

        # 异常类名：只在本行前面出现过「核异常」或「核抛出」时才算。
        # 这样 `核异常 除零错误：` 能转成 `except ZeroDivisionError:`，
        # 而用户在别处写「除零错误」当变量名时不受影响。
        if 名字 in 异常表 and self._在异常位置(s, i):
            return 异常表[名字]

        if 名字 in 关键词表:
            return 关键词表[名字]
        if 名字 in 函数表:
            return 函数表[名字]
        if 名字 in 英文关键词:
            return 名字
        if self._在赋值左边(s, i, j):
            return 名字
        if 名字 in 英文内置 and 名字 not in 已定义英文函数:
            self.记录(名字, "内置函数", 行, 列)
            return 名字
        return 名字

    # —— 字符串 ——

    def 尝试字符串(self, s, i):
        m = _字符串起点.match(s, i)
        if not m:
            return False
        py前缀 = m.group("py")
        he前缀 = m.group("he")
        if (py前缀 or he前缀) and i > 0 and 是标识符字符(s[i - 1]):
            return False

        前缀 = ""
        是f串 = False
        if py前缀:
            前缀 = py前缀
            是f串 = "f" in py前缀.lower()
        elif he前缀:
            前缀 = "f"
            是f串 = True

        引号 = m.group("q")
        内容起 = m.end()
        结束 = _找引号结束(s, 内容起, 引号)
        内容 = s[内容起:结束]

        if 是f串:
            内容 = self.处理f内容(内容, self.行, self.列)

        self.写(前缀 + 引号 + 内容 + 引号)
        if 结束 < len(s):
            self.前进(s[i:结束 + len(引号)])
            self._新位置 = 结束 + len(引号)
        else:
            self.前进(s[i:])
            self._新位置 = len(s)
        return True

    def 处理f内容(self, 内容, 行, 列):
        结果 = []
        i, n = 0, len(内容)
        cur行, cur列 = 行, 列
        while i < n:
            c = 内容[i]
            if c == "{":
                if 内容.startswith("{{", i):
                    结果.append("{{")
                    i += 2
                    cur列 += 2
                    continue
                结束 = _找字段结束(内容, i)
                if 结束 < 0:
                    结果.append(c)
                    i += 1
                    cur列 += 1
                    continue
                字段 = 内容[i + 1:结束]
                表达式, 后缀 = _切分字段(字段)
                译 = 转译(表达式, self.文件名, self.报告, cur行, cur列 + 1)
                结果.append("{" + 译 + 后缀 + "}")
                for ch in 内容[i:结束 + 1]:
                    if ch == "\n":
                        cur行, cur列 = cur行 + 1, 1
                    else:
                        cur列 += 1
                i = 结束 + 1
                continue
            结果.append(c)
            i += 1
            if c == "\n":
                cur行, cur列 = cur行 + 1, 1
            else:
                cur列 += 1
        return "".join(结果)


def 转译(源码, 文件名="<源码>", 报告=None, 行=1, 列=1):
    """把核语言源码转译成 Python 源码，行号保持不变。"""
    if 源码.startswith("﻿"):
        源码 = 源码[1:]
    return 转译器(文件名, 报告, 行, 列).转译(规范化源码(源码))


# ---------------------------------------------------------------------------
# 五、读文件、报告与错误显示
# ---------------------------------------------------------------------------


def 读源码(路径):
    with open(路径, "rb") as f:
        数据 = f.read()
    for 编码 in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return 数据.decode(编码)
        except UnicodeDecodeError:
            continue
    return 数据.decode("utf-8", errors="replace")


def 显示语法错误(源码, 译, e, 文件名, 流=None):
    流 = 流 or sys.stderr
    行号 = e.lineno or 0
    源行 = 源码.splitlines()
    译行 = 译.splitlines()
    原文 = 源行[行号 - 1] if 0 < 行号 <= len(源行) else ""
    译文 = 译行[行号 - 1] if 0 < 行号 <= len(译行) else ""
    流.write("语法错误：%s 第 %d 行\n" % (文件名, 行号))
    if 原文:
        流.write("  原文：%s\n" % 原文)
    if 译文 and 译文 != 原文:
        流.write("  转译：%s\n" % 译文)
    流.write("  原因：%s\n" % (e.msg or e))
    说明 = 异常说明.get(type(e).__name__)
    if 说明:
        流.write("  提示：%s\n" % 说明)
    流.flush()


def 显示运行错误(e, 源码, 文件名, 流=None):
    流 = 流 or sys.stderr
    类型 = type(e).__name__
    流.write("运行出错：%s：%s\n" % (类型, e))
    try:
        帧列表 = traceback.extract_tb(e.__traceback__)
    except Exception:
        帧列表 = []
    源行 = 源码.splitlines()
    相关 = [f for f in 帧列表 if f.filename == 文件名]
    显示 = 相关 if 相关 else 帧列表[-1:]
    for f in 显示[-4:]:
        行号 = f.lineno or 0
        行文 = 源行[行号 - 1].strip() if 0 < 行号 <= len(源行) else ""
        流.write("  第 %d 行，在 %s：%s\n" % (行号, f.name, 行文))
    说明 = 异常说明.get(类型)
    if 说明:
        流.write("  提示：%s\n" % 说明)
    # 「TypeError: 'xxx' object is not callable」多半是把内置名当变量赋值了，
    # 例如写了 `核说 = 3`，之后 `核说（...）` 就会这样。这里点明一下。
    提示 = _覆盖内置的线索(e, 源码)
    if 提示:
        流.write("  线索：%s\n" % 提示)
    流.flush()


def _覆盖内置的线索(e, 源码):
    """出错像是「内置名被当变量赋值后又被当函数用」时，给一句明确提示。

    只看异常文本不够（`'int' object is not callable` 里的 int 是类型名），
    所以改为扫源码：找出「对照表里的名字出现在赋值左边」的行，
    再看出错行有没有把这个名字当函数调用。
    """
    if "not callable" not in str(e) and not isinstance(e, NameError):
        return ""
    引用行 = ""
    类型 = getattr(e, "name", None)
    if not isinstance(e, NameError):
        # 从 traceback 里取最后一行的源码位置
        try:
            帧 = traceback.extract_tb(e.__traceback__)[-1]
            行号 = 帧.lineno or 0
            行集 = 源码.splitlines()
            引用行 = 行集[行号 - 1] if 0 < 行号 <= len(行集) else ""
        except Exception:
            引用行 = ""

    for 中, 英 in 函数表.items():
        # 源码里确实把这个名字赋过值
        if not re.search(r"^\s*%s\s*=" % re.escape(中), 源码, re.M):
            continue
        # 出错行里把它当函数调用（或直接引用）
        if 引用行 and (中 in 引用行 or (类型 and 类型 in 引用行)):
            return (
                "变量「%s」覆盖了内置函数 %s：源码里有 `%s = …` 这样的赋值。\n"
                "        换个变量名即可。" % (中, 英, 中)
            )
    return ""


# ---------------------------------------------------------------------------
# 六、编译与执行
# ---------------------------------------------------------------------------


def 编译源码(源码, 文件名, 报告=None, 流=None):
    """返回 (code, 译源码)。失败时已打印错误，code 为 None。"""
    译 = 转译(源码, 文件名, 报告)
    try:
        代码 = compile(译, 文件名, "exec")
    except SyntaxError as e:
        显示语法错误(源码, 译, e, 文件名, 流)
        return None, 译
    except ValueError as e:
        (流 or sys.stderr).write("编译失败：%s\n" % e)
        return None, 译
    return 代码, 译


def _当前脚本目录():
    """记住正在运行的主脚本所在目录，供 .xht 导入器兜底查找。"""
    return getattr(_当前脚本目录, "_值", "")


def _装xht导入器():
    """让 `核导入 工具` 能加载同目录的 工具.xht。

    做法是注册一个 meta path finder：遇到 .xht 文件时，用同一个转译器
    把中文源码转成 Python 再执行，得到的模块和普通 Python 模块一样可用。
    只认 .xht，不影响任何正常导入。
    """
    import importlib.abc
    import importlib.util
    import types

    if getattr(_装xht导入器, "_已装", False):
        return
    _装xht导入器._已装 = True

    class 加载器(importlib.abc.Loader):
        def __init__(self, 全路径):
            self.全路径 = 全路径

        def create_module(self, spec):
            return None

        def exec_module(self, module):
            源码 = 读源码(self.全路径)
            译 = 转译(源码, self.全路径, None)
            代码 = compile(译, self.全路径, "exec")
            exec(代码, module.__dict__)

    class 查找器(importlib.abc.MetaPathFinder):
        def find_spec(self, 全名, 搜索路径, 目标=None):
            末名 = 全名.rsplit(".", 1)[-1]
            # 搜索路径为 None 时（顶层导入），兜底再看当前工作目录与脚本目录
            目录集 = list(搜索路径) if 搜索路径 else []
            目录集 += [os.getcwd(), _当前脚本目录()]
            for 目录 in 目录集:
                if not 目录 or not os.path.isdir(目录):
                    continue
                候选 = os.path.join(目录, 末名 + 扩展名)
                if os.path.isfile(候选):
                    return importlib.util.spec_from_loader(
                        全名, 加载器(候选), origin=候选
                    )
            return None

    sys.meta_path.insert(0, 查找器())


def 执行代码(代码, 源码, 文件名, 参数=None, 流=None):
    全局 = {"__name__": "__main__", "__file__": 文件名, "__doc__": None}
    旧参数 = sys.argv
    sys.argv = [文件名] + list(参数 or [])
    # 让脚本所在目录可被导入，并按需把同目录的 .xht 当成模块
    脚本目录 = os.path.dirname(os.path.abspath(文件名)) if 文件名 else ""
    _当前脚本目录._值 = 脚本目录
    _旧路径 = list(sys.path)
    if 脚本目录 and os.path.isdir(脚本目录) and 脚本目录 not in sys.path:
        sys.path.insert(0, 脚本目录)
    _装xht导入器()
    try:
        exec(代码, 全局)
    except SystemExit as e:
        码 = e.code
        if 码 is None:
            return 0
        if isinstance(码, int):
            return 码
        print(码, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n已中断", file=sys.stderr)
        return 130
    except BaseException as e:  # noqa: BLE001 - 用户程序的异常都要接住
        显示运行错误(e, 源码, 文件名, 流)
        return 1
    finally:
        sys.argv = 旧参数
        sys.path[:] = _旧路径
    return 0


def 运行文件(路径, 参数=None, 报告路径=None):
    if not os.path.exists(路径):
        print("找不到文件：%s" % 路径, file=sys.stderr)
        return 2
    准备输出()
    准备输入()
    源码 = 读源码(路径)
    报告 = 未定义报告(报告路径 or 默认报告路径(路径))
    try:
        代码, _ = 编译源码(源码, 路径, 报告)
        if 代码 is None:
            return 1
        return 执行代码(代码, 源码, 路径, 参数)
    finally:
        报告.保存()


def 检查文件(路径):
    源码 = 读源码(路径)
    报告 = 未定义报告(默认报告路径(路径))
    try:
        代码, _ = 编译源码(源码, 路径, 报告)
    finally:
        报告.保存()
    if 代码 is None:
        return 1
    print("检查通过：%s" % 路径)
    return 0


def 转译文件(路径, 输出路径=None):
    源码 = 读源码(路径)
    报告 = 未定义报告(默认报告路径(路径))
    try:
        译 = 转译(源码, 路径, 报告)
    finally:
        报告.保存()
    if 输出路径:
        with open(输出路径, "w", encoding="utf-8", newline="\n") as f:
            f.write(译)
        print("已写出：%s" % 输出路径)
    else:
        准备输出()
        sys.stdout.write(译)
        if not 译.endswith("\n"):
            sys.stdout.write("\n")
    return 0


def 查看报告(路径=None):
    """查看未定义清单。

    带路径时看的是**那个文件所在目录**的清单（和运行时写出的位置一致）；
    不带路径时看当前目录的，并提示别的目录里可能也有。
    """
    报告路径 = 默认报告路径(路径) if 路径 else os.path.join(os.getcwd(), 未定义文件名)
    if not os.path.exists(报告路径):
        print("还没有未定义记录：%s" % 报告路径)
        if not 路径:
            print("提示：清单写在**运行的文件所在目录**下。", file=sys.stderr)
            print("      例如「核 报告 D:\\项目\\a.xht」会去看 D:\\项目\\未定义.txt。",
                  file=sys.stderr)
        return 0
    print("未定义清单：%s\n" % 报告路径)
    with open(报告路径, "r", encoding="utf-8") as f:
        sys.stdout.write(f.read())
    return 0


# ---------------------------------------------------------------------------
# 七、交互模式
# ---------------------------------------------------------------------------

退出词 = ("核退出", "退出", "exit", "exit()", "quit", "quit()")


def 交互模式():
    报告路径 = os.path.join(os.getcwd(), 未定义文件名)
    报告 = 未定义报告(报告路径)
    全局 = {"__name__": "__main__"}
    编译命令 = codeop.CommandCompiler()
    缓冲 = []
    print("%s %s" % (程序名, 版本))
    print("交互模式：输入 核退出 结束\n")
    while True:
        try:
            行 = input("核> " if not 缓冲 else "... ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not 缓冲 and 行.strip() in 退出词:
            break
        if not 缓冲 and not 行.strip():
            continue
        缓冲.append(行)
        源 = "\n".join(缓冲)
        try:
            译 = 转译(源, "<交互>", 报告)
            代码 = 编译命令(译, "<交互>", "exec")
        except SyntaxError as e:
            显示语法错误(源, 译, e, "<交互>")
            缓冲 = []
            continue
        except Exception as e:  # noqa: BLE001
            print("无法转译：%s" % e)
            缓冲 = []
            continue
        if 代码 is None:
            continue
        try:
            exec(代码, 全局)
        except SystemExit:
            break
        except BaseException as e:  # noqa: BLE001
            显示运行错误(e, 源, "<交互>")
        缓冲 = []
    报告.保存()
    return 0


# ---------------------------------------------------------------------------
# 八、命令行
# ---------------------------------------------------------------------------

帮助文本 = """%(名)s %(版)s —— 一门中文编程语言（源文件后缀 .%(扩展)s）

用法：
  核                          进入交互模式
  核 文件.%(扩展)s            运行程序
  核 运行 文件.%(扩展)s       运行程序（可带命令行参数）
  核 检查 文件.%(扩展)s       只检查语法，不运行
  核 转译 文件.%(扩展)s       打印转译后的 Python 代码
  核 转译 文件.%(扩展)s -o 输出.py
  核 报告                     查看未定义清单
  核 工坊                     打开图形界面（核工坊）
  核 版本                     查看版本
  核 帮助                     显示本帮助

说明：
  · 中英文符号视同，全角括号、冒号、逗号可以直接写。
  · 源码里出现、但对照表没有定义的英文写法，会原样交给 Python 执行，
    并记入当前目录的 未定义.txt，方便以后补进语言。
"""


def 打印帮助():
    print(帮助文本 % {"名": 程序名, "版": 版本, "扩展": 扩展名.lstrip(".")})


def 准备输出():
    """重定向到文件/管道时按 UTF-8 输出，控制台里仍用系统编码。"""
    for 流 in (sys.stdout, sys.stderr):
        try:
            if 流 is None:
                continue
            if 流.isatty():
                流.reconfigure(errors="replace")
                continue
            编码 = (getattr(流, "encoding", "") or "").lower().replace("-", "").replace("_", "")
            if 编码 != "utf8":
                流.reconfigure(encoding="utf-8", errors="replace")
            else:
                流.reconfigure(errors="replace")
        except Exception:
            pass


def 准备输入():
    """把标准输入也改成 UTF-8 读取，否则中文输入会变成乱码。

    问题只在打包后的 exe 上出现：源码运行时 stdin 是 utf-8，
    而 PyInstaller 打出来的 exe 里 stdin 的编码是 **gbk**（跟随系统代码页），
    于是 `说核()` 读到的「小明」被按 GBK 解码成「灏忔槑」。
    只修输出不修输入，用户就会觉得「在核工坊里输入中文是乱码」。

    注意：控制台里（isatty）如果改编码，可能与 Windows 控制台实际代码页
    不一致反而更糟，所以只对「非控制台」（管道/重定向，也就是 GUI 运行时
    的样子）改；控制台里保持系统默认。
    """
    流 = getattr(sys, "stdin", None)
    if 流 is None:
        return
    try:
        if 流.isatty():
            return
        编码 = (getattr(流, "encoding", "") or "").lower().replace("-", "").replace("_", "")
        if 编码 != "utf8":
            流.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def 命令行(argv):
    if not argv:
        return 交互模式()

    首 = argv[0]
    if 首 in ("版本", "--版本", "-v", "--version"):
        print("%s %s" % (程序名, 版本))
        print("Python %s" % sys.version.split()[0])
        return 0
    if 首 in ("帮助", "--帮助", "-h", "--help", "-?", "/?"):
        打印帮助()
        return 0
    if 首 in ("工坊", "界面", "gui", "--gui"):
        try:
            import 核工坊
        except ImportError as e:
            print("打不开图形界面：%s" % e, file=sys.stderr)
            print(
                "请确认 核工坊.py 与 核.py 在同一个文件夹，且使用的 Python 带 tkinter。",
                file=sys.stderr,
            )
            return 1
        return 核工坊.启动(argv[1:])

    if 首 in ("运行", "run"):
        if len(argv) < 2:
            print("用法：核 运行 文件.%(扩展)s [参数...]" % {"扩展": 扩展名.lstrip(".")}, file=sys.stderr)
            return 2
        return 运行文件(argv[1], argv[2:])

    if 首 in ("检查", "check"):
        if len(argv) < 2:
            print("用法：核 检查 文件%s" % 扩展名, file=sys.stderr)
            return 2
        return 检查文件(argv[1])

    if 首 in ("转译", "translate"):
        if len(argv) < 2:
            print("用法：核 转译 文件%s [-o 输出.py]" % 扩展名, file=sys.stderr)
            return 2
        输出 = None
        if "-o" in argv:
            k = argv.index("-o")
            if k + 1 < len(argv):
                输出 = argv[k + 1]
            else:
                print("-o 后面要跟输出文件路径", file=sys.stderr)
                return 2
        elif len(argv) > 2:
            # 常见误用：把输出路径直接当第二个参数写。
            # 直接忽略会让人以为「写了文件却没生成」，这里给个明确提示。
            多余 = argv[2]
            print(
                "提示：要写出到文件请用 -o，例如 核 转译 %s -o %s"
                % (argv[1], 多余),
                file=sys.stderr,
            )
            print("（当前仍只把结果打印到屏幕）", file=sys.stderr)
        return 转译文件(argv[1], 输出)

    if 首 in ("报告", "report"):
        return 查看报告(argv[1] if len(argv) > 1 else None)

    if 首.endswith(扩展名) or os.path.isfile(首):
        return 运行文件(首, argv[1:])

    print("不认识的命令：%s" % 首, file=sys.stderr)
    打印帮助()
    return 2


def 主入口():
    准备输出()
    准备输入()
    return 命令行(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(主入口())
