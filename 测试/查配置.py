# -*- coding: utf-8 -*-
"""配置写盘的原子性。

为什么单独测这个：存配置 以前直接 open(路径, "w")，写到一半崩溃/断电/
被杀进程就会留下半截 JSON；而 读配置 解析失败时是「静默返回 {}」，
用户下次打开软件发现主题、字号、行号、项目目录全没了，还没有任何提示。
改成「先写临时文件 + os.replace」之后，磁盘上要么是旧内容要么是新内容。

用法：python 测试/查配置.py
"""

import importlib
import json
import os
import sys
import tempfile

这里 = os.path.dirname(os.path.abspath(__file__))
根目录 = os.path.dirname(这里)
if 根目录 not in sys.path:
    sys.path.insert(0, 根目录)

临时 = tempfile.mkdtemp(prefix="核工坊配置_")
os.environ["核工坊_配置目录"] = 临时

import 配置  # noqa: E402

importlib.reload(配置)

问题 = []


def 检(说明, 条件, 详情=""):
    if 条件:
        print("  OK  %s" % 说明)
    else:
        问题.append(说明)
        print("  !! %s" % 说明)
        if 详情:
            print("        %s" % 详情)


路径 = 配置.配置路径()
print("== 一、正常读写 ==")
检("配置目录尊重环境变量", 配置.配置目录() == 临时, 配置.配置目录())
配置.存配置({"主题": "深色", "字号": 14, "最近": ["D:\\a.xht"]})
检("文件已写出", os.path.exists(路径))
读回 = 配置.读配置()
检("读回内容一致", 读回 == {"主题": "深色", "字号": 14, "最近": ["D:\\a.xht"]}, repr(读回))
with open(路径, encoding="utf-8") as f:
    明文 = f.read()
检("中文不转义", "深色" in 明文, 明文[:60])

print("== 二、不留临时文件 ==")
残留 = [n for n in os.listdir(临时) if n.endswith(".tmp")]
检("目录里没有 .tmp 残留", not 残留, repr(残留))

print("== 三、覆盖写不会写坏原文件 ==")
with open(路径, encoding="utf-8") as f:
    原内容 = json.loads(f.read())
配置.存配置({"主题": "浅色"})
检("覆盖后内容正确", 配置.读配置() == {"主题": "浅色"})
检("覆盖前的内容仍可解析", isinstance(原内容, dict))

print("== 四、半截 JSON 时读配置不炸（并暴露会静默重置这一事实）==")
with open(路径, "w", encoding="utf-8") as f:
    f.write('{"主题": "深')          # 故意写坏
检("读坏文件返回空字典而不是抛异常", 配置.读配置() == {})
# 重新写回好的内容，确认还能恢复
配置.存配置({"主题": "深色"})
检("坏文件之后仍能正常写入", 配置.读配置() == {"主题": "深色"})

print("== 五、写入失败也不抛（目录不可用时）==")
坏目录 = os.path.join(临时, "被占用")
os.makedirs(坏目录, exist_ok=True)
os.environ["核工坊_配置目录"] = 坏目录
try:
    # 让目标路径变成一个目录，写文件必然失败
    os.makedirs(os.path.join(坏目录, "工坊配置.json"), exist_ok=True)
    配置.存配置({"主题": "深色"})
    检("写失败时不抛异常", True)
    检("写失败时也不留 .tmp", not os.path.exists(os.path.join(坏目录, "工坊配置.json.tmp")))
except Exception as e:  # noqa: BLE001
    检("写失败时不抛异常", False, str(e))
os.environ["核工坊_配置目录"] = 临时

print("== 六、坏类型 / 坏 JSON 不能让程序启动崩溃（P1-7）==")
# 以前 读配置 只挡住「JSON 解析失败」，一旦解析成功就原样返回。
# 而配置文件是可以被手改、被旧版本写、被同步工具截断的。实测这几种
# 「合法 JSON、错误类型」全都会让程序**启动即崩**：
#   [] / "文本" / 123 / null → AttributeError: 'list' object has no attribute 'get'
#   制表宽="abc"             → ValueError: invalid literal for int()
#   项目目录=123             → TypeError: expected str, bytes or os.PathLike … not int
#   窗口尺寸=123             → TypeError: argument of type 'int' is not iterable
坏用例 = [
    ("空列表", [], {}),
    ("字符串", "文本", {}),
    ("数字", 123, {}),
    ("null", None, {}),
    ("制表宽=abc", {"制表宽": "abc"}, {}),
    ("制表宽=0（越界）", {"制表宽": 0}, {}),
    ("制表宽=999（越界）", {"制表宽": 999}, {}),
    ("项目目录=123", {"项目目录": 123}, {}),
    ("项目目录=空白串", {"项目目录": "   "}, {}),
    ("最近=abc", {"最近": "abc"}, {}),
    ("窗口尺寸=123", {"窗口尺寸": 123}, {}),
    ("窗口位置=123", {"窗口位置": 123}, {}),
    ("字号=abc", {"字号": "abc"}, {}),
    ("缩进线=字符串", {"缩进线": "yes"}, {}),
]
for 名, 内容, 期望 in 坏用例:
    with open(路径, "w", encoding="utf-8") as f:
        if isinstance(内容, str) and 内容.startswith("{"):
            f.write(内容)
        else:
            json.dump(内容, f)
    try:
        读回 = 配置.读配置()
        正常 = isinstance(读回, dict) and 读回 == 期望
        详情 = "返回 %r（期望 %r）" % (读回, 期望)
    except Exception as e:  # noqa: BLE001
        正常 = False
        详情 = "%s: %s" % (type(e).__name__, e)
    检("%s → 不崩且回退默认" % 名, 正常, 详情)

# 坏字段丢了，**好字段一个都不能动**（不能因为清洗把用户设置洗没了）
with open(路径, "w", encoding="utf-8") as f:
    json.dump({"制表宽": "abc", "行号": False, "主题": "浅色", "字号": 20}, f)
读回 = 配置.读配置()
检("坏字段被丢掉", "制表宽" not in 读回, repr(读回))
检("好字段原样保留",
   读回.get("行号") is False and 读回.get("主题") == "浅色" and 读回.get("字号") == 20,
   repr(读回))
检("坏字段有留痕（不是为了静默吞掉）", bool(配置.上次问题), repr(配置.上次问题))

# 半截 JSON 也要留痕
with open(路径, "w", encoding="utf-8") as f:
    f.write('{"主题": "深')
配置.读配置()
检("坏 JSON 也留痕", bool(配置.上次问题), repr(配置.上次问题))

# 最近列表里的非字符串项要被摘掉，字符串项保留
with open(路径, "w", encoding="utf-8") as f:
    json.dump({"最近": ["a.xht", 5, None, "b.xht"]}, f)
读回 = 配置.读配置()
检("最近里的非字符串项被摘掉", 读回.get("最近") == ["a.xht", "b.xht"], repr(读回.get("最近")))

print("== 首次运行：没有配置文件不算坏 ==")
# 回归：FileNotFoundError 以前和坏 JSON 走同一条 except，
# 于是全新安装第一次打开就提示「有设置被重置成默认」，纯属误报。
os.remove(路径)
读回 = 配置.读配置()
检(读回 == {}, "没有配置文件时返回空配置")
检(not 配置.上次问题, "首次运行不留「坏配置」痕迹（实际 %r）" % (配置.上次问题,))

print("== Tk 旧版与 Qt 版共用同一份配置规则 ==")
# 回归：Tk 版以前自带一套「json.load 成功就原样返回」的读法，
# 同一个 工坊配置.json，Qt 认为该丢掉的坏字段，Tk 直接 int() 炸在启动里。
# 实测四种形状都能让 Tk 主窗口.__init__ 抛异常。
import 核工坊 as Tk版  # noqa: E402

检(Tk版.配置路径() == 配置.配置路径(), "两版指向同一个配置文件")
for 名, 内容 in (
    ("字号是字符串", {"字号": "abc"}),
    ("字号是 null", {"字号": None}),
    ("顶层是列表", [1, 2, 3]),
    ("窗口尺寸是数字", {"窗口尺寸": 123}),
    ("项目目录是数字", {"项目目录": 123}),
    ("最近是字符串", {"最近": "a.xht"}),
):
    with open(路径, "w", encoding="utf-8") as f:
        json.dump(内容, f)
    读 = Tk版.读配置()
    try:
        # 复刻 Tk 主窗口.__init__ 里那几行取值
        int(读.get("字号", 12))
        读.get("项目目录") or "默认"
        尺寸 = 读.get("窗口尺寸", "1380x860")
        if "x" not in 尺寸:
            raise TypeError("窗口尺寸不是 WxH")
        for p in 读.get("最近", []):
            os.path.isfile(p)
        检(True, "Tk 读「%s」不炸" % 名)
    except Exception as e:  # noqa: BLE001
        检(False, "Tk 读「%s」会炸：%s: %s" % (名, type(e).__name__, e))

print()
print("=" * 62)
if 问题:
    print("发现 %d 处配置问题：" % len(问题))
    for 项 in 问题:
        print("  · %s" % 项)
    sys.exit(1)
print("配置读写正常（原子写、失败不炸）")
