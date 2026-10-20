#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""核工坊 —— 核语言的图形界面（PyCharm 风格，第一版）

功能：项目管理、标签页编辑器、语法高亮、行号、运行/停止、控制台交互输入、
语法检查、查找替换、语法对照表、深/浅色主题。只依赖标准库 tkinter。

启动：核 工坊     或     python 核工坊.py [文件.xht]
"""

import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, font as tkfont, messagebox, ttk

def _资源根目录():
    """源码运行时是脚本所在目录；PyInstaller 单文件下是解包临时目录。"""
    打包目录 = getattr(sys, "_MEIPASS", None)
    if 打包目录:
        return 打包目录
    return os.path.dirname(os.path.abspath(__file__))


这里 = _资源根目录()
if 这里 not in sys.path:
    sys.path.insert(0, 这里)

import 核 as 内核  # noqa: E402
import 圆角  # noqa: E402

#: 打包成 exe 时由 启动器.py 填入自身路径；源码运行时为 None。
宿主EXE = None

标题 = "核工坊"
副标题 = "核语言 集成开发环境"

# ---------------------------------------------------------------------------
# 主题
# ---------------------------------------------------------------------------

深色 = {
    "名": "深色",
    # 层次：窗口 < 编辑器 < 面板；避免一片同色
    "窗口": "#1e1f22",
    "编辑器": "#1e1f22",
    "面板": "#2b2d30",
    "面板2": "#26282b",
    "边框": "#393b40",
    "文本": "#dfe1e5",
    "次要文本": "#9da0a8",
    "行号底": "#1e1f22",
    "行号字": "#5c6068",
    "当前行": "#23252a",
    "选区": "#2f5d9e",
    "光标": "#dfe1e5",
    "关键字": "#cf8e6d",
    "内置": "#d5b778",
    "方法": "#d5b778",
    "字符串": "#6aab73",
    "数字": "#2aacb8",
    "注释": "#7a7e85",
    "函数名": "#56a8f5",
    "控制台底": "#1e1f22",
    "控制台字": "#c8cad0",
    "错误": "#f75464",
    "输入": "#6aab73",
    "命令": "#7a7e85",
    "按钮": "#393b40",
    "按钮热": "#43454a",
    "选中行": "#2e436e",
    "标签未选": "#2b2d30",
    "强调": "#56a8f5",
    "标题栏": "#2b2d30",
    "工具条": "#2b2d30",
    "工具条热": "#393b40",
    "工具条选中": "#393b40",
    "缩进线": "#34373c",
    "面包屑": "#1e1f22",
    "面包屑字": "#8b8f96",
    "标签选中底线": "#56a8f5",
    "运行条": "#1e1f22",
    "状态栏": "#2b2d30",
    "分组标题": "#c9ccd3",
    "圆角": 10,
    "圆角小": 6,
    "按钮圆角": 8,
}

浅色 = {
    "名": "浅色",
    "窗口": "#eceef1",
    "编辑器": "#ffffff",
    "面板": "#f7f8fa",
    "面板2": "#f2f4f6",
    "边框": "#d6dae0",
    "文本": "#1f2329",
    "次要文本": "#6b7280",
    "行号底": "#f7f8fa",
    "行号字": "#a0a5ad",
    "当前行": "#f2f6fc",
    "选区": "#cfe2ff",
    "光标": "#1f2329",
    "关键字": "#8f4e00",
    "内置": "#8a6d00",
    "方法": "#8a6d00",
    "字符串": "#067d17",
    "数字": "#1750eb",
    "注释": "#9aa0a6",
    "函数名": "#005fab",
    "控制台底": "#ffffff",
    "控制台字": "#3a3f45",
    "错误": "#c7221f",
    "输入": "#067d17",
    "命令": "#9aa0a6",
    "按钮": "#e6e9ed",
    "按钮热": "#d8dce2",
    "选中行": "#d5e5ff",
    "标签未选": "#f2f4f6",
    "强调": "#3574f0",
    "标题栏": "#f7f8fa",
    "工具条": "#f7f8fa",
    "工具条热": "#e6e9ed",
    "工具条选中": "#e6e9ed",
    "缩进线": "#e3e6ea",
    "面包屑": "#ffffff",
    "面包屑字": "#7a8087",
    "标签选中底线": "#3574f0",
    "运行条": "#ffffff",
    "状态栏": "#f7f8fa",
    "分组标题": "#3a3f45",
    "圆角": 10,
    "圆角小": 6,
    "按钮圆角": 8,
}

主题集 = {"深色": 深色, "浅色": 浅色}

界面字体 = ("Microsoft YaHei UI", 9)
等宽字体候选 = ("Cascadia Mono", "Consolas", "Courier New")

# ---------------------------------------------------------------------------
# 语法高亮的规则
# ---------------------------------------------------------------------------


def _构造高亮式():
    中文词 = sorted(
        (set(内核.关键词表) | {"核核"}) - {""}, key=len, reverse=True
    )
    中文内置 = sorted(set(内核.函数表) | set(内核.方法表), key=len, reverse=True)
    英文词 = sorted(
        set(内核.英文关键词) | {"print", "input", "len", "range", "int", "float", "str"},
        key=len,
        reverse=True,
    )
    片段 = [
        r"(?P<注释>核核[^\n]*|#[^\n]*)",
        r"""(?P<字符串>核?[rRbBuUfF]{0,2}(?:'''[\s\S]*?'''|""\"[\s\S]*?""\"|"[^"\n]*"|'[^'\n]*'))""",
        r"(?P<数字>\b0[xX][0-9a-fA-F]+\b|\b0[bB][01]+\b|\b\d[\d_]*(?:\.\d+)?(?:[eE][+-]?\d+)?\b)",
        r"(?P<函数名>(?<=核定义\s)[^\s(（:：]+|(?<=def\s)[A-Za-z_\u4e00-\u9fff][\w\u4e00-\u9fff]*)",
        r"\.\s*(?P<方法>[A-Za-z_\u4e00-\u9fff][\w\u4e00-\u9fff]*)",
        r"(?P<关键字>" + "|".join(中文词) + r"|\b(?:" + "|".join(英文词) + r")\b)",
        r"(?P<内置>" + "|".join(中文内置) + r"|\b(?:" + "|".join(内核.英文内置) + r")\b)",
    ]
    return __import__("re").compile("|".join(片段))


高亮式 = _构造高亮式()

# ---------------------------------------------------------------------------
# 小工具
# ---------------------------------------------------------------------------


def 读配置():
    try:
        with open(os.path.join(这里, "工坊配置.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def 存配置(配置):
    try:
        with open(os.path.join(这里, "工坊配置.json"), "w", encoding="utf-8") as f:
            json.dump(配置, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def 规范化路径(p):
    return os.path.normpath(os.path.abspath(p))


def 挑选等宽字体(根):
    可选 = set(tkfont.families(根))
    for 名 in 等宽字体候选:
        if 名 in 可选:
            return 名
    return "Courier New"


def 生成图标(根, 类型):
    """用 PhotoImage 画 16×16 的小图标（工具栏/项目树用）。"""
    图 = tk.PhotoImage(width=16, height=16)
    if 类型 == "文件夹":
        图.put("#e8c26a", to=(1, 4, 15, 14))
        图.put("#d9b25a", to=(1, 4, 7, 7))
        图.put("#b98f35", to=(1, 13, 15, 14))
    elif 类型 == "核":
        图.put("#4a88c7", to=(3, 1, 13, 15))
        图.put("#ffffff", to=(5, 4, 11, 5))
        for y in (7, 9, 11):
            图.put("#ffffff", to=(5, y, 10, y + 1))
    elif 类型 == "打开":
        图.put("#4a88c7", to=(2, 5, 14, 14))
        图.put("#7fb3e0", to=(2, 5, 14, 7))
        图.put("#ffffff", to=(4, 9, 12, 10))
    elif 类型 == "运行":
        图.put("#5ca45c", to=(4, 2, 6, 14))
        图.put("#5ca45c", to=(7, 4, 9, 12))
        图.put("#5ca45c", to=(10, 5, 12, 11))
    elif 类型 == "停止":
        图.put("#cf5b56", to=(4, 4, 12, 12))
    elif 类型 == "保存":
        图.put("#8fbcbb", to=(3, 2, 13, 14))
        图.put("#2b2b2b", to=(5, 3, 11, 7))
        图.put("#e6e6e6", to=(4, 9, 12, 14))
    elif 类型 == "设置":
        颜色 = "#9da0a8"
        图.put(颜色, to=(7, 1, 9, 15))
        图.put(颜色, to=(1, 7, 15, 9))
        图.put(颜色, to=(3, 3, 5, 5))
        图.put(颜色, to=(11, 3, 13, 5))
        图.put(颜色, to=(3, 11, 5, 13))
        图.put(颜色, to=(11, 11, 13, 13))
        图.put("#1e1f22", to=(6, 6, 10, 10))
    return 图


#: 项目自带的图标文件（原子轨道 + 彩色立方体）。
图标目录 = os.path.join(这里, "素材")
图标PNG = os.path.join(图标目录, "核图标.png")
图标ICO = os.path.join(图标目录, "核图标.ico")
_图标缓存 = {}


#: 图标缓存按「Tk 根窗口」分开存：PhotoImage 绑定到创建它的解释器，
#: 若全局共用，第一个窗口销毁后缓存的图片会失效（image doesn't exist）。
_图标缓存 = {}


def 缩放图标(根, 边长):
    """按目标边长缩放项目图标；超出 tkinter 缩放能力时用 PIL，最后退回 subsample。"""
    键 = (id(根), 边长)
    if 键 in _图标缓存:
        return _图标缓存[键]
    原图 = None
    try:
        from PIL import Image, ImageTk

        图 = Image.open(图标PNG).convert("RGBA")
        图.thumbnail((边长, 边长), Image.LANCZOS)
        原图 = ImageTk.PhotoImage(图, master=根)
    except Exception:
        原图 = None
    if 原图 is None and os.path.exists(图标PNG):
        try:
            基 = tk.PhotoImage(file=图标PNG, master=根)
            倍 = max(1, max(基.width(), 基.height()) // max(1, 边长))
            if 倍 > 1:
                基 = 基.subsample(倍, 倍)
            原图 = 基
        except tk.TclError:
            原图 = None
    # 只保留最近一个根窗口的缓存，避免窗口反复开关时无限增长
    当前根 = id(根)
    for 旧键 in [k for k in _图标缓存 if k[0] != 当前根]:
        del _图标缓存[旧键]
    _图标缓存[键] = 原图
    return 原图


def 界面图标尺寸(根, 逻辑边长):
    """按当前 DPI 缩放取合适像素尺寸（高 DPI 下 20 逻辑像素 = 30 实际像素）。"""
    try:
        倍 = max(1.0, 根.winfo_fpixels("1i") / 96.0)
    except tk.TclError:
        倍 = 1.0
    return 缩放图标(根, int(round(逻辑边长 * 倍)))


def 设窗口图标(根, 尝试=0):
    """把语言图标设成标题栏/任务栏图标。

    必须在窗口真正显示之后再调用：窗口处于 withdraw 状态时设置，
    Tk 在重新映射时会丢掉。窗口初始化过程中会被重新映射多次
    （pack 布局变化、PanedWindow 首次排布、分栏调整），因此这里
    安排几次重试，确保最终标题栏用的是我们的图标。
    """
    成功 = False
    for 尺寸 in (16, 32, 48, 64, 128, 256):
        路径 = os.path.join(图标目录, "核图标_%d.png" % 尺寸)
        if not os.path.exists(路径):
            continue
        try:
            图 = tk.PhotoImage(file=路径, master=根)
            根.iconphoto(True, 图)
            根._图标图 = 图  # 必须持有引用，否则会被回收
            成功 = True
            break
        except tk.TclError:
            continue
    if os.path.exists(图标ICO):
        try:
            根.iconbitmap(default=图标ICO)
            成功 = True
        except (tk.TclError, OSError):
            pass

    根._图标已设 = 成功
    if 成功 and 尝试 < 4:
        # 布局仍在变化时图标可能被重置，隔一段时间再设一遍
        try:
            根.after(200 + 尝试 * 300, lambda: 设窗口图标(根, 尝试 + 1))
        except tk.TclError:
            pass
    return 成功


class 圆角按钮(tk.Canvas):
    """真正画圆角的工具栏按钮。

    Tk 8.6 没有原生圆角控件，这里用 Canvas 画圆角底 + 文本/图标，
    悬停时换底色，和 PyCharm 新 UI 的按钮观感一致。
    """

    def __init__(self, 父, 文本, 命令, 主题, 图标=None, 提示=None, 内边距=(10, 5)):
        self.配置 = 主题
        self.命令 = 命令
        self.文本 = 文本
        self.图标 = 图标
        字体 = 界面字体
        测 = tkfont.Font(font=字体)
        图宽 = 图标.width() + 6 if 图标 is not None else 0
        宽 = 测.measure(文本) + 图宽 + 内边距[0] * 2
        高 = max(测.metrics("linespace"), 图标.height() if 图标 else 0) + 内边距[1] * 2
        super().__init__(
            父,
            width=宽,
            height=高,
            bg=主题["工具条"],
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self._画(主题["工具条"], 主题["文本"])
        self.bind("<Button-1>", lambda e: self.命令())
        self.bind("<Enter>", self._进入)
        self.bind("<Leave>", self._离开)

    def _画(self, 底色, 前景):
        主题 = self.配置
        self.delete("all")
        self.configure(bg=主题["工具条"])
        宽 = int(self.cget("width"))
        高 = int(self.cget("height"))
        半径 = 主题.get("按钮圆角", 8)
        圆角.圆角矩形(
            self, 1, 1, 宽 - 1, 高 - 1, 半径, fill=底色, outline=""
        )
        测 = tkfont.Font(font=界面字体)
        文本宽 = 测.measure(self.文本)
        图宽 = self.图标.width() + 6 if self.图标 is not None else 0
        起 = (宽 - (文本宽 + 图宽)) / 2
        if self.图标 is not None:
            self.create_image(
                起, 高 / 2, image=self.图标, anchor="w"
            )
            self.image = self.图标
        起点 = 起 + 图宽
        self.create_text(
            起点, 高 / 2, text=self.文本, anchor="w", fill=前景, font=界面字体
        )

    def _进入(self, _e=None):
        self._画(self.配置["按钮热"], self.配置["文本"])

    def _离开(self, _e=None):
        self._画(self.配置["工具条"], self.配置["文本"])

    def 换主题(self, 主题):
        self.配置 = 主题
        self._画(主题["工具条"], 主题["文本"])


def 挂提示(控件, 文本):
    """轻量气泡提示。"""
    if not 文本:
        return
    提示 = {"窗": None}

    def 显示(_e=None):
        if 提示["窗"] is not None:
            return
        x = 控件.winfo_rootx() + 12
        y = 控件.winfo_rooty() + 控件.winfo_height() + 8
        窗 = tk.Toplevel(控件)
        窗.wm_overrideredirect(True)
        窗.wm_geometry("+%d+%d" % (x, y))
        标签 = tk.Label(
            窗,
            text=文本,
            bg="#4a4a4a",
            fg="#f0f0f0",
            padx=8,
            pady=4,
            font=("Microsoft YaHei UI", 9),
            relief="flat",
        )
        标签.pack()
        提示["窗"] = 窗

    def 隐藏(_e=None):
        if 提示["窗"] is not None:
            提示["窗"].destroy()
            提示["窗"] = None

    控件.bind("<Enter>", 显示, add="+")
    控件.bind("<Leave>", 隐藏, add="+")
    控件.bind("<ButtonPress>", 隐藏, add="+")


# ---------------------------------------------------------------------------
# 编辑器
# ---------------------------------------------------------------------------


class 编辑器(tk.Frame):
    def __init__(self, 主窗, 文件路径=None):
        super().__init__(主窗.编辑器容器, bg=主窗.主题["编辑器"], bd=0, highlightthickness=0)
        self.主窗 = 主窗
        self.文件路径 = 文件路径
        self.已改 = False
        self.换行标记 = "\n"

        self.行号画布 = tk.Canvas(
            self, width=56, bg=主窗.主题["行号底"], highlightthickness=0, bd=0
        )
        self.行号画布.pack(side="left", fill="y")

        self.滚动 = ttk.Scrollbar(self, orient="vertical")
        self.滚动.pack(side="right", fill="y")

        self.文本 = tk.Text(
            self,
            wrap="none",
            undo=True,
            maxundo=-1,
            autoseparators=True,
            bd=0,
            highlightthickness=0,
            bg=主窗.主题["编辑器"],
            fg=主窗.主题["文本"],
            insertbackground=主窗.主题["光标"],
            insertwidth=2,
            selectbackground=主窗.主题["选区"],
            selectforeground="#ffffff" if 主窗.主题 is 深色 else "#1f1f1f",
            font=主窗.等宽字体,
            padx=8,
            pady=6,
            spacing1=1,
            spacing3=1,
            tabs=("%d" % (主窗.制表宽 * 主窗.字宽,)),
        )
        self.文本.pack(side="left", fill="both", expand=True)
        self.滚动.configure(command=self._滚动)
        self.文本.configure(yscrollcommand=self._同步滚动)
        self.横向滚动 = ttk.Scrollbar(self, orient="horizontal")
        self.横向滚动.pack(side="bottom", fill="x")
        self.横向滚动.configure(command=self.文本.xview)
        self.文本.configure(xscrollcommand=self.横向滚动.set)
        self.文本.configure(wrap="none")

        self._配置标签()
        self._绑定()
        self.行号画布.bind("<Button-1>", lambda e: None)
        self.文本.focus_set()

    # —— 颜色与标签 ——

    def _配置标签(self):
        主题 = self.主窗.主题
        文本 = self.文本
        文本.tag_configure("关键字", foreground=主题["关键字"])
        文本.tag_configure("内置", foreground=主题["内置"])
        文本.tag_configure("方法", foreground=主题["方法"])
        文本.tag_configure("字符串", foreground=主题["字符串"])
        文本.tag_configure("数字", foreground=主题["数字"])
        文本.tag_configure("注释", foreground=主题["注释"])
        文本.tag_configure("函数名", foreground=主题["函数名"], font=self.主窗.粗体)
        文本.tag_configure("当前行", background=主题["当前行"])
        文本.tag_configure(
            "查找结果", background=主题["选中行"], foreground="#ffffff"
        )
        文本.tag_configure(
            "缩进线",
            foreground=主题["缩进线"],
            font=(self.主窗.等宽字体[0], self.主窗.等宽字体[1]),
        )
        文本.tag_lower("当前行")
        文本.tag_lower("缩进线")
        文本.configure(
            bg=主题["编辑器"],
            fg=主题["文本"],
            insertbackground=主题["光标"],
            selectbackground=主题["选区"],
        )
        self.行号画布.configure(bg=主题["行号底"])

    # —— 绑定 ——

    def _绑定(self):
        t = self.文本
        t.bind("<KeyRelease>", self._键松开)
        t.bind("<ButtonRelease-1>", self._键松开)
        t.bind("<<Modified>>", self._被修改)
        t.bind("<Return>", self._回车)
        t.bind("<Tab>", self._制表)
        t.bind("<Shift-Tab>", self._反制表)
        t.bind("<Control-z>", self._撤销)
        t.bind("<Control-y>", self._重做)
        t.bind("<Control-/>", lambda e: self.主窗.注释切换())
        t.bind("<MouseWheel>", self._滚轮, add="+")
        self.行号画布.bind("<MouseWheel>", self._滚轮)
        t.bind("<Control-MouseWheel>", self._缩放, add="+")
        self.行号画布.bind("<Configure>", lambda e: self._画行号())
        t.bind("<Configure>", lambda e: self._画行号())

    def _滚轮(self, 事件):
        self.文本.yview_scroll(int(-事件.delta / 120) or 0, "units")
        self._画行号()
        return "break"

    def _缩放(self, 事件):
        self.主窗.改字号(1 if 事件.delta > 0 else -1)
        return "break"

    def _撤销(self, _e=None):
        try:
            self.文本.edit_undo()
        except tk.TclError:
            pass
        return "break"

    def _重做(self, _e=None):
        try:
            self.文本.edit_redo()
        except tk.TclError:
            pass
        return "break"

    def _被修改(self, _e=None):
        if self.文本.edit_modified():
            self.已改 = True
            self.主窗.刷新标签(self)
            self.主窗.高亮延时(self)
            self.文本.edit_modified(False)

    def _键松开(self, _e=None):
        self.主窗.更新状态栏()
        self.主窗.高亮延时(self)
        self._当前行()
        self._画行号()

    def _回车(self, _e=None):
        self.文本.edit_separator()
        行号 = self.文本.index("insert").split(".")[0]
        本行 = self.文本.get(行号 + ".0", 行号 + ".end")
        缩进 = ""
        for 字 in 本行:
            if 字 in " \t":
                缩进 += 字
            else:
                break
        新增 = ""
        if 本行.rstrip().endswith((":", "：", "(", "[", "{", "（", "［", "｛")):
            新增 = " " * self.主窗.制表宽
        self.文本.insert("insert", "\n" + 缩进 + 新增)
        self.文本.see("insert")
        self.文本.edit_separator()
        return "break"

    def _制表(self, _e=None):
        if self.文本.tag_ranges("sel"):
            self.主窗.缩进行(1)
            return "break"
        self.文本.insert("insert", " " * (self.主窗.制表宽 - self._列偏移()))
        return "break"

    def _反制表(self, _e=None):
        self.主窗.缩进行(-1)
        return "break"

    def _列偏移(self):
        列 = int(self.文本.index("insert").split(".")[1])
        return 列 % self.主窗.制表宽

    # —— 滚动与行号 ——

    def _滚动(self, *参数):
        self.文本.yview(*参数)
        self._画行号()

    def _同步滚动(self, 首, 末):
        self.滚动.set(首, 末)
        self._画行号()

    def _画行号(self):
        画布 = self.行号画布
        画布.delete("all")
        if not self.主窗.显示行号 or 画布.winfo_width() <= 1:
            return
        主题 = self.主窗.主题
        画布.configure(bg=主题["行号底"])
        行高 = self.主窗.行高
        高 = max(画布.winfo_height(), 行高)
        try:
            首行 = int(self.文本.index("@0,0").split(".")[0])
            末行 = int(self.文本.index("@0,%d" % 高).split(".")[0])
        except tk.TclError:
            return
        if 首行 < 1:
            首行 = 1
        当前 = int(self.文本.index("insert").split(".")[0])
        宽 = 画布.winfo_width()
        for 行 in range(首行, 末行 + 2):
            try:
                info = self.文本.dlineinfo("%d.0" % 行)
            except tk.TclError:
                info = None
            if not info:
                continue
            y = info[1]
            颜色 = 主题["文本"] if 行 == 当前 else 主题["行号字"]
            if 行 == 当前:
                画布.create_rectangle(0, y, 宽, y + info[3], fill=主题["行号底"], outline="")
            画布.create_text(
                宽 - 8,
                y + 2,
                anchor="ne",
                text=str(行),
                fill=颜色,
                font=self.主窗.行号字体,
            )

    def _当前行(self):
        self.文本.tag_remove("当前行", "1.0", "end")
        if not self.主窗.显示行号:
            return
        行 = self.文本.index("insert").split(".")[0]
        self.文本.tag_add("当前行", "%s.0" % 行, "%s.0+1line" % 行)

    # —— 内容 ——

    def 取文本(self):
        return self.文本.get("1.0", "end-1c")

    def 置文本(self, 内容):
        self.文本.delete("1.0", "end")
        self.文本.insert("1.0", 内容)
        self.文本.edit_reset()
        self.文本.edit_modified(False)
        self.已改 = False
        self.主窗.高亮(self)
        self._画行号()
        self._当前行()

    def 行数(self):
        return int(self.文本.index("end-1c").split(".")[0])

    def 换主题(self):
        self._配置标签()
        self.主窗.高亮(self)
        self._画行号()
        self._当前行()

    def 加粗(self):
        self.文本.tag_configure("函数名", font=self.主窗.粗体)

    def 画缩进参考线(self, 开启, 制表宽, 主题):
        """在正文背后画竖线。

        Tk 的 Text 不能直接画线，这里用「文本同级 + 逐字符着色」的轻量方案：
        给每级缩进的最后一个空格上色，视觉上就是一条竖点线，且不影响编辑。
        """
        文本 = self.文本
        文本.tag_remove("缩进线", "1.0", "end")
        文本.tag_configure("缩进线", foreground=主题["缩进线"])
        if not 开启 or 制表宽 <= 0:
            return
        try:
            首行 = int(文本.index("@0,0").split(".")[0])
            末行 = int(文本.index("@0,%d" % max(1, 文本.winfo_height())).split(".")[0])
        except tk.TclError:
            return
        for 行 in range(首行, min(末行 + 1, 首行 + 400)):
            原文 = 文本.get("%d.0" % 行, "%d.end" % 行)
            if not 原文.strip():
                continue
            缩进 = len(原文) - len(原文.lstrip(" "))
            for 列 in range(制表宽, 缩进 + 1, 制表宽):
                文本.tag_add("缩进线", "%d.%d" % (行, 列 - 1), "%d.%d" % (行, 列))


class 查找框(tk.Toplevel):
    def __init__(self, 主窗):
        super().__init__(主窗.根)
        self.主窗 = 主窗
        self.title("查找 / 替换")
        self.transient(主窗.根)
        self.resizable(False, False)
        self.主题 = 主窗.主题
        self.configure(bg=self.主题["面板"])
        self.属性 = {"查找": tk.StringVar(), "替换": tk.StringVar(), "区分": tk.BooleanVar(value=False)}

        框 = tk.Frame(self, bg=self.主题["面板"], padx=12, pady=10)
        框.pack(fill="both", expand=True)
        行1 = tk.Frame(框, bg=self.主题["面板"])
        行1.pack(fill="x", pady=2)
        tk.Label(行1, text="查找：", bg=self.主题["面板"], fg=self.主题["文本"], font=界面字体).pack(side="left")
        self.查找框 = tk.Entry(
            行1,
            textvariable=self.属性["查找"],
            width=34,
            bg=self.主题["编辑器"],
            fg=self.主题["文本"],
            insertbackground=self.主题["光标"],
            relief="flat",
        )
        self.查找框.pack(side="left", ipady=3)

        行2 = tk.Frame(框, bg=self.主题["面板"])
        行2.pack(fill="x", pady=2)
        tk.Label(行2, text="替换：", bg=self.主题["面板"], fg=self.主题["文本"], font=界面字体).pack(side="left")
        tk.Entry(
            行2,
            textvariable=self.属性["替换"],
            width=34,
            bg=self.主题["编辑器"],
            fg=self.主题["文本"],
            insertbackground=self.主题["光标"],
            relief="flat",
        ).pack(side="left", ipady=3)

        行3 = tk.Frame(框, bg=self.主题["面板"])
        行3.pack(fill="x", pady=(6, 2))
        tk.Checkbutton(
            行3,
            text="区分大小写",
            variable=self.属性["区分"],
            bg=self.主题["面板"],
            fg=self.主题["文本"],
            selectcolor=self.主题["编辑器"],
            activebackground=self.主题["面板"],
            activeforeground=self.主题["文本"],
            font=界面字体,
        ).pack(side="left")

        按钮行 = tk.Frame(框, bg=self.主题["面板"])
        按钮行.pack(fill="x", pady=(8, 0))
        for 文本, 命令 in (
            ("查找下一个", self.查找下一个),
            ("替换", self.替换),
            ("全部替换", self.全部替换),
            ("关闭", self.destroy),
        ):
            tk.Button(
                按钮行,
                text=文本,
                command=命令,
                bg=self.主题["按钮"],
                fg=self.主题["文本"],
                relief="flat",
                padx=10,
                pady=3,
                font=界面字体,
                activebackground=self.主题["按钮热"],
                activeforeground=self.主题["文本"],
                bd=0,
            ).pack(side="left", padx=3)

        self.bind("<Return>", lambda e: self.查找下一个())
        self.bind("<Escape>", lambda e: self.destroy())
        self.查找框.focus_set()
        try:
            选中 = 主窗.当前编辑器().文本.get("sel.first", "sel.last")
            if 选中:
                self.属性["查找"].set(选中.split("\n")[0])
        except tk.TclError:
            pass

    def _编辑器(self):
        return self.主窗.当前编辑器()

    def 查找下一个(self):
        编 = self._编辑器()
        if 编 is None:
            return
        文本 = 编.文本
        词 = self.属性["查找"].get()
        if not 词:
            return
        开始 = text_index = 文本.index("insert")
        位置 = 文本.search(词, 开始, stopindex="end", nocase=not self.属性["区分"].get())
        if not 位置:
            位置 = 文本.search(词, "1.0", stopindex="end", nocase=not self.属性["区分"].get())
        if not 位置:
            self.bell()
            return
        文本.tag_remove("sel", "1.0", "end")
        文本.mark_set("insert", 位置)
        文本.see(位置)
        文本.tag_add("sel", 位置, "%s+%dc" % (位置, len(词)))
        文本.focus_set()

    def 替换(self):
        编 = self._编辑器()
        if 编 is None:
            return
        文本 = 编.文本
        try:
            选中 = 文本.get("sel.first", "sel.last")
        except tk.TclError:
            选中 = ""
        if 选中 and (
            选中 == self.属性["查找"].get()
            or (not self.属性["区分"].get() and 选中.lower() == self.属性["查找"].get().lower())
        ):
            文本.insert("sel.first", self.属性["替换"].get())
        self.查找下一个()

    def 全部替换(self):
        编 = self._编辑器()
        if 编 is None:
            return
        词 = self.属性["查找"].get()
        新词 = self.属性["替换"].get()
        if not 词:
            return
        文本 = 编.文本
        原文 = 文本.get("1.0", "end-1c")
        if self.属性["区分"].get():
            次数 = 原文.count(词)
            新文 = 原文.replace(词, 新词)
        else:
            import re as _re

            新文, 次数 = _re.subn(_re.escape(词), 新词.replace("\\", "\\\\"), 原文, flags=_re.I)
        if 次数:
            文本.delete("1.0", "end")
            文本.insert("1.0", 新文)
            编.已改 = True
        self.主窗.状态("替换了 %d 处" % 次数)


# ---------------------------------------------------------------------------
# 主窗口
# ---------------------------------------------------------------------------


class 主窗口:
    def __init__(self):
        self.这里 = 这里
        self.根 = tk.Tk()
        self.根.withdraw()
        self.根.title(标题)
        self.配置 = 读配置()
        self.主题 = 主题集.get(self.配置.get("主题", "深色"), 深色)
        self.字号 = int(self.配置.get("字号", 12))
        self.制表宽 = 4
        self.显示行号 = bool(self.配置.get("行号", True))
        self.显示项目树 = bool(self.配置.get("项目树", True))
        self.显示对照表 = bool(self.配置.get("对照表", False))
        self.显示缩进线 = bool(self.配置.get("缩进线", True))
        self.项目目录 = self.配置.get("项目目录") or os.getcwd()
        self.最近 = self.配置.get("最近", [])
        self.文档集 = []
        self.当前 = None
        self.进程 = None
        self.输出队列 = queue.Queue()
        self.运行标记 = 0
        self.查找窗 = None
        self._高亮任务 = None
        self._轮询任务 = None
        self._缩放任务 = None
        self._已退出 = False
        self._构建字体()
        self._建界面()
        self._绑快捷键()
        self.根.protocol("WM_DELETE_WINDOW", self.退出)
        self.根.bind("<Configure>", self._窗口缩放)
        self.根.deiconify()
        self._设窗口尺寸()
        self._轮询任务 = self.根.after(60, self._轮询输出)
        self._初始打开()
        self.根.after(60, self._定分栏)
        self.根.after(400, self._定分栏)
        self.根.after(80, self._启用拖放)
        self.根.after(40, self._应用窗口圆角)
        # 图标必须在窗口真正显示之后再设，否则会被 Tk 丢掉
        self.根.after(10, lambda: 设窗口图标(self.根))
        self._刷新标题()

    def _应用窗口圆角(self):
        """Win11 上使用原生圆角窗口，并把标题栏染成主题色。"""
        try:
            标题色 = self.主题["标题栏"]
            圆角.窗口圆角(
                self.根,
                标题栏色=圆角.hex转rgb(标题色),
                边框色=圆角.hex转rgb(self.主题["边框"]),
                深色=(self.主题["名"] == "深色"),
            )
        except Exception:
            pass

    def _启用拖放(self):
        """接受把文件/文件夹拖进窗口。"""
        try:
            import 拖放
        except ImportError:
            return
        结果 = 拖放.启用拖放(self.根, self._处理拖入)
        if 结果:
            self.状态("提示：可以把 .xht 文件直接拖进窗口打开")

    def _处理拖入(self, 路径集):
        """处理拖入的路径：目录→设为项目，.xht→打开，其它→提示。"""
        已开 = 0
        for 路径 in 路径集:
            if os.path.isdir(路径):
                self.项目目录 = 规范化路径(路径)
                self._装载项目树(self.项目目录)
                self.状态("项目已切换为 %s" % self.项目目录)
                self.存配置()
            elif 路径.lower().endswith(内核.扩展名):
                if self.打开(路径):
                    已开 += 1
            else:
                self.状态("只能打开 %s 文件，已忽略：%s" % (内核.扩展名, os.path.basename(路径)))
        if 已开:
            self.状态("已打开 %d 个文件" % 已开)
            self.根.deiconify()
            self.根.lift()

    def 销毁(self):
        """清理定时任务与子进程后销毁窗口（供测试/脚本安全关闭）。"""
        self._已退出 = True
        for 名 in ("_缩放任务", "_高亮任务", "_轮询任务"):
            任务 = getattr(self, 名, None)
            if 任务:
                try:
                    self.根.after_cancel(任务)
                except (tk.TclError, ValueError):
                    pass
                setattr(self, 名, None)
        if self.进程 is not None and self.进程.poll() is None:
            try:
                self.进程.kill()
            except OSError:
                pass
            self._收尾进程(self.进程)
            self.进程 = None
        try:
            self.根.destroy()
        except tk.TclError:
            pass

    def _窗口缩放(self, 事件=None):
        """窗口尺寸变化时保证编辑区不被压没。"""
        if 事件 is not None and 事件.widget is not self.根:
            return
        if getattr(self, "_缩放任务", None):
            try:
                self.根.after_cancel(self._缩放任务)
            except tk.TclError:
                pass
        self._缩放任务 = self.根.after(120, self._定分栏)

    def _定分栏(self):
        """运行窗口占下方约 30%，并随窗口高度收缩。

        小窗口下若还按固定下限给高度，编辑区会被挤得看不见，
        所以上下限都跟着总高走。
        """
        try:
            self.根.update_idletasks()
            总高 = self.分栏.winfo_height()
            if 总高 < 320:
                return
            下限 = max(130, min(190, int(总高 * 0.26)))
            上限 = max(下限, min(340, int(总高 * 0.42)))
            下 = max(下限, min(上限, int(总高 * 0.30)))
            self.分栏.sash_place(0, 0, 总高 - 下)
        except tk.TclError:
            pass

    def _设窗口尺寸(self):
        保存 = self.配置.get("窗口尺寸", "")
        宽 = 高 = None
        if 保存 and "x" in 保存:
            try:
                尺寸 = 保存.split("+")[0].split("x")
                宽, 高 = int(尺寸[0]), int(尺寸[1])
            except (ValueError, IndexError):
                宽 = 高 = None
        if 宽 is None or 宽 < 800 or 高 is None or 高 < 560:
            宽, 高 = 1380, 860
        屏宽 = self.根.winfo_screenwidth()
        屏高 = self.根.winfo_screenheight()
        宽 = max(min(宽, 屏宽 - 80), 900)
        高 = max(min(高, 屏高 - 100), 620)
        x = max(0, (屏宽 - 宽) // 2)
        y = max(0, (屏高 - 高) // 2 - 20)
        self.根.geometry("%dx%d+%d+%d" % (宽, 高, x, y))

    def _当前尺寸(self):
        """保存窗口尺寸；窗口还没映射时返回配置里的旧值。"""
        try:
            宽 = self.根.winfo_width()
            高 = self.根.winfo_height()
        except tk.TclError:
            return self.配置.get("窗口尺寸", "1380x860")
        if 宽 < 400 or 高 < 300:
            return self.配置.get("窗口尺寸", "1380x860")
        return "%dx%d+%d+%d" % (宽, 高, self.根.winfo_rootx(), self.根.winfo_rooty())

    # —— 字体与尺寸 ——

    def _构建字体(self):
        根 = self.根
        try:
            dpi = 根.winfo_fpixels("1i")
            根.tk.call("tk", "scaling", dpi / 72.0)
        except Exception:
            pass
        族 = 挑选等宽字体(根)
        self.等宽字体 = (族, self.字号)
        self.行号字体 = (族, max(8, self.字号 - 1))
        self.粗体 = (族, self.字号, "bold")
        测 = tkfont.Font(font=self.等宽字体)
        self.字宽 = 测.measure("0") or 8
        self.行高 = 测.metrics("linespace") or 18
        self.界面字体 = 界面字体
        # 顶栏品牌图标的实际像素边长，用来推算工具栏高度
        try:
            倍 = max(1.0, 根.winfo_fpixels("1i") / 96.0)
        except tk.TclError:
            倍 = 1.0
        self.品牌高 = int(round(26 * 倍))

    def 改字号(self, 差, 存配置=True):
        self.字号 = max(8, min(28, self.字号 + 差))
        self._构建字体()
        for 文档 in self.文档集:
            文档.文本.configure(font=self.等宽字体)
            文档.行号字体 = self.行号字体
            文档.加粗()
            文档._画行号()
            self.高亮(文档)
        控制台 = getattr(self, "控制台", None)
        if 控制台 is not None:
            控制台.configure(font=self.等宽字体)
            控制台.tag_configure("命令", font=self.等宽字体)
        self.状态("字号 %d" % self.字号)
        if 存配置:
            self.存配置()

    # —— 界面搭建 ——

    def _建界面(self):
        根 = self.根
        主题 = self.主题
        根.configure(bg=主题["窗口"])

        self.图标 = {
            "运行": 生成图标(根, "运行"),
            "停止": 生成图标(根, "停止"),
            "保存": 生成图标(根, "保存"),
            "文件夹": 生成图标(根, "文件夹"),
            "核": 界面图标尺寸(根, 16),
            "打开": 界面图标尺寸(根, 18),
            "品牌": 界面图标尺寸(根, 22),
            "设置": 生成图标(根, "设置"),
        }

        self._建标题栏()
        self._建主工具条()

        # 主体：左工具条 | 中部三栏（编辑器 + 底部运行窗口）
        self.主体 = tk.Frame(根, bg=主题["窗口"])
        self.主体.pack(fill="both", expand=True)

        self._建左工具条()

        self.分栏 = tk.PanedWindow(
            self.主体, orient="vertical", bg=主题["窗口"], bd=0, sashwidth=5, sashrelief="flat"
        )
        self.分栏.pack(side="left", fill="both", expand=True)

        self.中部 = tk.Frame(self.分栏, bg=主题["窗口"])
        self.分栏.add(self.中部, stretch="always", minsize=220)

        self.中部.grid_rowconfigure(0, weight=1)
        self.中部.grid_columnconfigure(0, weight=0)
        self.中部.grid_columnconfigure(1, weight=1)
        self.中部.grid_columnconfigure(2, weight=0)
        self.中部.grid_columnconfigure(2, minsize=280)
        self._建项目树(self.中部)
        self._建编辑区(self.中部)
        self._建侧栏(self.中部)
        self._建控制台()
        self._建状态栏()
        self._建菜单()
        self.应用主题()

    # —— 顶部：集成式标题栏 + 工具条 + 左侧竖排 → 严格模仿 PyCharm 新 UI ——

    def _建标题栏(self):
        """最上面一条：应用标 + 项目名 + 面包屑；右侧窗口按钮由系统绘制。"""
        主题 = self.主题
        self.标题栏 = 条 = tk.Frame(self.根, bg=主题["标题栏"], height=32)
        条.pack(side="top", fill="x")
        条.pack_propagate(False)

        self.品牌图 = tk.Label(条, image=self.图标["品牌"] if self.图标["品牌"] else None,
                             bg=主题["标题栏"], bd=0)
        if self.图标["品牌"] is None:
            self.品牌图.configure(text="核", fg=主题["错色"] if "错色" in 主题 else "#e8e8e8",
                                font=("Microsoft YaHei UI", 11, "bold"))
        self.品牌图.pack(side="left", padx=(8, 2))

        self.项目名标 = tk.Label(
            条,
            text=" 核工坊  v%s" % 内核.版本,
            bg=主题["标题栏"],
            fg=主题["文本"],
            font=("Microsoft YaHei UI", 9),
        )
        self.项目名标.pack(side="left")

        # 汉堡菜单（≡）：放右侧，点开完整菜单
        self.汉堡 = tk.Label(
            条, text="≡", bg=主题["标题栏"], fg=主题["面包屑字"],
            font=("Microsoft YaHei UI", 13), padx=10, cursor="hand2",
        )
        self.汉堡.pack(side="right")
        挂提示(self.汉堡, "主菜单（文件 / 编辑 / 运行 / 视图 / 帮助）")

        # 搜索框（PyCharm 的 Find Anything，这里做「查找」入口）
        self.搜索框 = tk.Entry(
            条,
            bg=主题["面板2"],
            fg=主题["文本"],
            insertbackground=主题["光标"],
            relief="flat",
            font=界面字体,
            width=18,
        )
        self.搜索框.pack(side="right", padx=(0, 8), pady=4, ipady=2)
        self.搜索框.bind("<Return>", lambda e: self.查找替换())
        挂提示(self.搜索框, "搜索（直接按回车打开查找框）")

    def _建主工具条(self):
        """文件操作 + 运行控制 + 右侧面包屑。

        职责划分：这里放「动作」，左侧竖条管「面板开关」，
        运行窗口工具条只在有输出时才用。
        """
        主题 = self.主题
        self.主工具条 = 条 = tk.Frame(self.根, bg=主题["工具条"])
        条.pack(side="top", fill="x")

        self.按钮集 = []
        定义 = (
            ("运行", self.运行, self.图标["运行"], "运行当前文件（F5）"),
            ("停止", self.停止, self.图标["停止"], "停止运行（Shift+F5）"),
            ("保存", self.保存, self.图标["保存"], "保存当前文件（Ctrl+S）"),
            ("打开", self.打开文件, self.图标["打开"], "打开 .xht 文件（Ctrl+O）"),
            ("设置", self.打开设置, self.图标["设置"], "设置（Ctrl+,）"),
        )
        for 文本, 命令, 图标, 提示 in 定义:
            钮 = 圆角按钮(条, 文本, 命令, 主题, 图标=图标)
            钮.pack(side="left", padx=2, pady=5)
            挂提示(钮, 提示)
            self.按钮集.append(钮)

        # 右侧：面包屑（项目 / 文件 / 光标所在函数），模仿 PyCharm 的路径条
        self.面包屑 = tk.Label(
            条,
            text="",
            bg=主题["工具条"],
            fg=主题["面包屑字"],
            font=界面字体,
            anchor="e",
            padx=10,
        )
        self.面包屑.pack(side="right")

    def _建左工具条(self):
        """最左侧竖排图标条：项目 / 结构 / 对照表 / 运行 / 设置。"""
        主题 = self.主题
        self.左条 = 条 = tk.Frame(
            self.主体 if hasattr(self, "主体") else self.根,
            bg=主题["工具条"],
            width=34,
        )
        条.pack(side="left", fill="y")
        条.pack_propagate(False)
        self.左按钮 = {}
        定义 = (
            ("项目", "◱", "项目栏（Ctrl+1）", self.切换项目树),
            ("对照表", "☰", "语法对照表", self.切换对照表),
        )
        for 键, 字, 提示, 命令 in 定义:
            钮 = tk.Label(
                条,
                text=字,
                bg=主题["工具条"],
                fg=主题["面包屑字"],
                font=("Microsoft YaHei UI", 12),
                pady=7,
                cursor="hand2",
            )
            钮.pack(fill="x")
            钮.bind("<Button-1>", lambda e, c=命令: c())
            钮.bind("<Enter>", lambda e, w=钮: w.configure(bg=self.主题["工具条热"]))
            钮.bind("<Leave>", lambda e, w=钮: w.configure(bg=self.主题["工具条"]))
            挂提示(钮, 提示)
            self.左按钮[键] = 钮

        底 = tk.Frame(条, bg=主题["工具条"])
        底.pack(side="bottom", fill="x")
        for 字, 提示, 命令 in (("⚙", "设置（Ctrl+,）", self.打开设置),):
            钮 = tk.Label(
                底, text=字, bg=主题["工具条"], fg=主题["面包屑字"],
                font=("Microsoft YaHei UI", 12), pady=6, cursor="hand2",
            )
            钮.pack(fill="x")
            钮.bind("<Button-1>", lambda e, c=命令: c())
            挂提示(钮, 提示)


    def _建项目树(self, 父):
        主题 = self.主题
        self.项目框 = tk.Frame(父, bg=主题["面板2"], width=230, height=120)
        self.项目框.grid(row=0, column=0, sticky="nsew")
        self.项目框.grid_propagate(False)
        self.项目框.pack_propagate(False)
        self.项目标题 = 标题行 = tk.Frame(self.项目框, bg=主题["面板"])
        标题行.pack(fill="x")
        tk.Label(
            标题行,
            text="∨  项目",
            bg=主题["面板"],
            fg=主题["分组标题"],
            font=("Microsoft YaHei UI", 9, "bold"),
            anchor="w",
            padx=6,
            pady=5,
        ).pack(side="left")
        # PyCharm 分组标题右侧的小按钮：全部收起 / 更多
        for 字, 命令, 提示 in (
            ("⊟", self.收起项目树, "全部收起"),
            ("⋯", self.打开文件夹, "打开文件夹"),
        ):
            钮 = tk.Label(
                标题行, text=字, bg=主题["面板"], fg=主题["次要文本"],
                font=("Microsoft YaHei UI", 10), padx=5, cursor="hand2",
            )
            钮.pack(side="right")
            钮.bind("<Button-1>", lambda e, c=命令: c())
            挂提示(钮, 提示)
        self.项目路径标签 = tk.Label(
            标题行,
            text="",
            bg=主题["面板"],
            fg=主题["次要文本"],
            font=("Microsoft YaHei UI", 8),
        )
        self.项目路径标签.pack(side="right", padx=4)

        样式 = ttk.Style()
        self.树样式名 = "项目树.Treeview"
        self.树 = ttk.Treeview(
            self.项目框,
            show="tree",
            selectmode="browse",
            style=self.树样式名,
            padding=(6, 2),
        )
        self.树.pack(fill="both", expand=True)
        self.树.bind("<<TreeviewOpen>>", self._展开节点)
        self.树.bind("<Double-1>", self._双击树)
        self.树.bind("<Return>", self._双击树)
        滚动 = ttk.Scrollbar(self.项目框, orient="vertical", command=self.树.yview)
        滚动.pack(side="right", fill="y")
        self.树.configure(yscrollcommand=滚动.set)

    def 收起项目树(self):
        for 节点 in self.树.get_children(""):
            self.树.item(节点, open=False)
        self.状态("已收起项目树")

    def _建编辑区(self, 父):
        主题 = self.主题
        self.编辑框 = tk.Frame(父, bg=主题["窗口"])
        self.编辑框.grid(row=0, column=1, sticky="nsew")

        self.标签栏 = tk.Frame(self.编辑框, bg=主题["工具条"], height=38)
        self.标签栏.pack(side="top", fill="x")
        self.标签栏.pack_propagate(False)
        # 右侧留一个「新标签」按钮位，让整条底色连贯
        self.新标签钮 = tk.Label(
            self.标签栏,
            text="+",
            bg=主题["工具条"],
            fg=主题["面包屑字"],
            font=("Microsoft YaHei UI", 12),
            padx=8,
            cursor="hand2",
        )
        self.新标签钮.pack(side="right", padx=(0, 4))
        self.新标签钮.bind("<Button-1>", lambda e: self.新建())
        挂提示(self.新标签钮, "新建文件")

        # PyCharm 的编辑器面包屑：项目 › 文件 › 函数
        self.编辑面包屑 = tk.Label(
            self.编辑框,
            text="",
            bg=主题["面包屑"],
            fg=主题["面包屑字"],
            font=("Microsoft YaHei UI", 8),
            anchor="w",
            padx=10,
            pady=2,
        )
        self.编辑面包屑.pack(side="top", fill="x")

        self.编辑器容器 = tk.Frame(self.编辑框, bg=主题["编辑器"])
        self.编辑器容器.pack(fill="both", expand=True)
        self.编辑器容器.grid_rowconfigure(0, weight=1)
        self.编辑器容器.grid_columnconfigure(0, weight=1)

        self.欢迎 = tk.Frame(self.编辑器容器, bg=主题["编辑器"])
        self.欢迎.grid(row=0, column=0, sticky="nsew")
        # 用 grid 居中：place 的相对定位在编辑器被项目树挤窄后会算偏，内容会跑出可视区
        self.欢迎.grid_rowconfigure(0, weight=1)
        self.欢迎.grid_columnconfigure(0, weight=1)
        框 = tk.Frame(self.欢迎, bg=主题["编辑器"])
        框.grid(row=0, column=0)
        self.欢迎图 = 缩放图标(self.根, 72)
        if self.欢迎图 is not None:
            self.欢迎图标 = tk.Label(框, image=self.欢迎图, bg=主题["编辑器"], bd=0)
            self.欢迎图标.pack(pady=(0, 10))
        tk.Label(
            框,
            text="核语言",
            bg=主题["编辑器"],
            fg=主题["文本"],
            font=("Microsoft YaHei UI", 22, "bold"),
        ).pack()
        tk.Label(
            框,
            text="用中文写程序",
            bg=theme_safe(主题, "编辑器"),
            fg=主题["次要文本"],
            font=("Microsoft YaHei UI", 11),
        ).pack(pady=(2, 18))
        提示 = (
            "新建文件（Ctrl+N）开始写第一个核程序\n"
            "核说（“你好，世界！”）\n\n"
            "F5 运行    Ctrl+S 保存    Ctrl+O 打开"
        )
        self.欢迎提示 = tk.Label(
            框,
            text=提示,
            bg=主题["编辑器"],
            fg=主题["次要文本"],
            font=("Microsoft YaHei UI", 9),
            justify="center",
            wraplength=420,
        )
        self.欢迎提示.pack()

    def _建侧栏(self, 父):
        主题 = self.主题
        self.侧框 = tk.Frame(父, bg=主题["面板2"], width=280, height=120)
        self.侧框.grid(row=0, column=2, sticky="nsew")
        self.侧框.grid_propagate(False)
        self.侧框.pack_propagate(False)
        self.侧栏标题 = 标题行 = tk.Frame(self.侧框, bg=主题["面板"])
        标题行.pack(fill="x")
        tk.Label(
            标题行,
            text="语法对照表",
            bg=主题["面板"],
            fg=主题["次要文本"],
            font=("Microsoft YaHei UI", 9, "bold"),
            anchor="w",
            padx=10,
            pady=6,
        ).pack(side="left")
        self.对照搜索 = tk.Entry(
            self.侧框,
            bg=主题["编辑器"],
            fg=主题["文本"],
            relief="flat",
            insertbackground=主题["光标"],
            font=界面字体,
        )
        self.对照搜索.pack(fill="x", padx=8, pady=(6, 4), ipady=3)
        self.对照搜索.bind("<KeyRelease>", lambda e: self._填对照表())
        self.对照表 = tk.Text(
            self.侧框,
            bg=主题["面板2"],
            fg=主题["文本"],
            relief="flat",
            bd=0,
            padx=10,
            pady=6,
            font=self.等宽字体,
            wrap="none",
            cursor="arrow",
        )
        self.对照表.pack(fill="both", expand=True)
        self.对照表.configure(state="disabled")
        self._对照标签()
        self._填对照表()

    def 主窗粗体(self):
        return ("Microsoft YaHei UI", 9, "bold")

    def _对照标签(self):
        主题 = self.主题
        表 = self.对照表
        表.tag_configure("类", foreground=主题["关键字"], font=self.主窗粗体())
        表.tag_configure("中", foreground=主题["文本"])
        表.tag_configure("号", foreground=主题["次要文本"])
        表.tag_configure("英", foreground=主题["内置"])
        表.tag_configure("说", foreground=主题["次要文本"])

    def _建控制台(self):
        主题 = self.主题
        self.下框 = tk.Frame(self.分栏, bg=主题["面板2"], height=210)
        self.下框.pack_propagate(False)

        # 运行窗口顶部：竖排工具条（重跑/停止/清空/未定义清单）+ 标签
        self.运行工具条 = 工具条 = tk.Frame(self.下框, bg=主题["面板"], width=34)
        工具条.pack(side="left", fill="y")
        工具条.pack_propagate(False)
        self.运行钮集 = []
        for 字, 命令, 提示 in (
            ("↻", self.运行, "重新运行（F5）"),
            ("✕", self.清空控制台, "清空输出"),
            ("≡", self.打开未定义清单, "未定义清单"),
        ):
            钮 = tk.Label(
                工具条, text=字, bg=主题["面板"], fg=主题["次要文本"],
                font=("Microsoft YaHei UI", 11), pady=4, cursor="hand2",
            )
            钮.pack(fill="x", pady=1)
            钮.bind("<Button-1>", lambda e, c=命令: c())
            挂提示(钮, 提示)
            self.运行钮集.append(钮)

        右区 = tk.Frame(self.下框, bg=主题["面板2"])
        右区.pack(side="left", fill="both", expand=True)

        self.输出标题行 = 标题行 = tk.Frame(右区, bg=主题["面板"])
        标题行.pack(fill="x")
        self.输出标题 = tk.Label(
            标题行,
            text="运行",
            bg=主题["面板"],
            fg=主题["文本"],
            font=("Microsoft YaHei UI", 9, "bold"),
            padx=10,
            pady=5,
        )
        self.输出标题.pack(side="left")
        间隔 = tk.Frame(标题行, bg=主题["面板"])
        间隔.pack(side="right", expand=True, fill="both")
        self.运行状态 = tk.Label(
            标题行,
            text="就绪",
            bg=主题["面板"],
            fg=主题["次要文本"],
            font=界面字体,
            padx=10,
        )
        self.运行状态.pack(side="right")

        # 输入行先占住底部，再让控制台填满剩余空间；
        # 否则控制台 expand=True 会把输入行挤出可视区域，看起来像「卡住」。
        self.输入行 = 输入行 = tk.Frame(右区, bg=主题["面板"], height=44)
        输入行.pack(side="bottom", fill="x")
        输入行.pack_propagate(False)
        self.输入提示 = tk.Label(
            输入行,
            text="输入",
            bg=主题["面板"],
            fg=主题["次要文本"],
            font=界面字体,
            padx=8,
            pady=2,
        )
        self.输入提示.pack(side="left")
        self.输入框 = tk.Entry(
            输入行,
            bg=主题["面板2"],
            fg=主题["文本"],
            insertbackground=主题["光标"],
            disabledbackground=主题["面板2"],
            disabledforeground=主题["次要文本"],
            relief="flat",
            bd=0,
            state="disabled",
            font=self.等宽字体,
        )
        self.输入框.pack(fill="x", expand=True, padx=(0, 8), pady=5)
        self.输入框.bind("<Return>", self._发送输入)
        发送钮 = tk.Label(
            输入行,
            text="发送",
            bg=主题["面板"],
            fg=主题["次要文本"],
            font=界面字体,
            padx=10,
            cursor="hand2",
        )
        发送钮.pack(side="right")
        发送钮.bind("<Button-1>", lambda e: self._发送输入())
        挂提示(发送钮, "把这一行发给正在运行的程序（回车同效）")

        self.控制台 = tk.Text(
            右区,
            bg=主题["运行条"],
            fg=主题["控制台字"],
            relief="flat",
            bd=0,
            padx=10,
            pady=6,
            font=self.等宽字体,
            wrap="word",
            state="disabled",
            cursor="arrow",
        )
        self.控制台.pack(side="top", fill="both", expand=True)
        self.控制台.tag_configure("错误", foreground=主题["错误"])
        self.控制台.tag_configure("命令", foreground=主题["命令"])
        self.控制台.tag_configure("输入", foreground=主题["输入"])
        self.控制台.tag_configure("提示", foreground=主题["强调"])
        self.控制台.tag_configure("命令", font=self.等宽字体)

        self.分栏.add(self.下框, height=210, minsize=90)

    def _建状态栏(self):
        主题 = self.主题
        条 = tk.Frame(self.根, bg=主题["状态栏"], height=26)
        条.pack(side="bottom", fill="x")
        条.pack_propagate(False)
        self.状态信息 = tk.Label(
            条, text="就绪", bg=主题["状态栏"], fg=主题["次要文本"], font=界面字体, padx=10, anchor="w"
        )
        self.状态信息.pack(side="left")
        # 右侧：行列、选中数、编码、缩进、语言（模仿 PyCharm 状态栏的密集信息）
        self.位置信息 = tk.Label(
            条, text="行 1，列 1", bg=主题["状态栏"], fg=主题["次要文本"], font=界面字体, padx=8
        )
        self.位置信息.pack(side="right")
        self.分隔1 = tk.Label(
            条, text="│", bg=主题["状态栏"], fg=主题["边框"], font=界面字体
        )
        self.分隔1.pack(side="right")
        self.编码信息 = tk.Label(
            条, text="UTF-8", bg=主题["状态栏"], fg=主题["次要文本"], font=界面字体, padx=8
        )
        self.编码信息.pack(side="right")
        self.缩进信息 = tk.Label(
            条, text="空格 4", bg=主题["状态栏"], fg=主题["次要文本"], font=界面字体, padx=8
        )
        self.缩进信息.pack(side="right")
        self.语言信息 = tk.Label(
            条, text="核语言", bg=主题["状态栏"], fg=主题["次要文本"], font=界面字体, padx=8
        )
        self.语言信息.pack(side="right")
        self.状态条 = 条

    def _建菜单(self):
        主题 = self.主题
        菜单栏 = tk.Menu(self.根, tearoff=0, bg=主题["面板"], fg=主题["文本"], font=界面字体)
        # 圆角风格：不占用窗口顶部一条系统菜单，改由标题栏的 ≡ 汉堡按钮弹出
        if self.配置.get("隐藏菜单栏", True):
            self.根.configure(menu="")
        else:
            self.根.configure(menu=菜单栏)

        文件 = tk.Menu(菜单栏, tearoff=0, font=界面字体)
        文件.add_command(label="新建", accelerator="Ctrl+N", command=self.新建)
        文件.add_command(label="打开…", accelerator="Ctrl+O", command=self.打开文件)
        文件.add_command(label="打开文件夹…", command=self.打开文件夹)
        文件.add_separator()
        文件.add_command(label="保存", accelerator="Ctrl+S", command=self.保存)
        文件.add_command(label="另存为…", accelerator="Ctrl+Shift+S", command=self.另存为)
        文件.add_separator()
        self.最近菜单 = tk.Menu(文件, tearoff=0, font=界面字体)
        文件.add_cascade(label="最近打开", menu=self.最近菜单)
        self._填最近菜单()
        文件.add_separator()
        文件.add_command(label="关闭标签", accelerator="Ctrl+W", command=self.关闭当前)
        文件.add_command(label="退出", command=self.退出)
        菜单栏.add_cascade(label="文件", menu=文件)

        编辑 = tk.Menu(菜单栏, tearoff=0, font=界面字体)
        编辑.add_command(label="撤销", accelerator="Ctrl+Z", command=lambda: self.当前编辑器()._撤销())
        编辑.add_command(label="重做", accelerator="Ctrl+Y", command=lambda: self.当前编辑器()._重做())
        编辑.add_separator()
        编辑.add_command(label="剪切", accelerator="Ctrl+X", command=lambda: self.当前编辑器().文本.event_generate("<<Cut>>"))
        编辑.add_command(label="复制", accelerator="Ctrl+C", command=lambda: self.当前编辑器().文本.event_generate("<<Copy>>"))
        编辑.add_command(label="粘贴", accelerator="Ctrl+V", command=lambda: self.当前编辑器().文本.event_generate("<<Paste>>"))
        编辑.add_command(label="全选", accelerator="Ctrl+A", command=self.全选)
        编辑.add_separator()
        编辑.add_command(label="查找 / 替换…", accelerator="Ctrl+F", command=self.查找替换)
        编辑.add_command(label="转到行…", accelerator="Ctrl+G", command=self.转到行)
        编辑.add_command(label="注释 / 取消注释", accelerator="Ctrl+/", command=self.注释切换)
        菜单栏.add_cascade(label="编辑", menu=编辑)

        运行 = tk.Menu(菜单栏, tearoff=0, font=界面字体)
        运行.add_command(label="运行", accelerator="F5", command=self.运行)
        运行.add_command(label="停止", accelerator="Shift+F5", command=self.停止)
        运行.add_separator()
        运行.add_command(label="检查语法", accelerator="F9", command=self.检查语法)
        运行.add_command(label="查看未定义清单", command=self.打开未定义清单)
        菜单栏.add_cascade(label="运行", menu=运行)

        视图 = tk.Menu(菜单栏, tearoff=0, font=界面字体)
        self.主题变量 = tk.StringVar(value=self.主题["名"])
        视图.add_radiobutton(label="深色主题", value="深色", variable=self.主题变量, command=lambda: self.换主题("深色"))
        视图.add_radiobutton(label="浅色主题", value="浅色", variable=self.主题变量, command=lambda: self.换主题("浅色"))
        视图.add_separator()
        视图.add_command(label="增大字号", accelerator="Ctrl+滚轮", command=lambda: self.改字号(1))
        视图.add_command(label="减小字号", command=lambda: self.改字号(-1))
        视图.add_separator()
        self.行号变量 = tk.BooleanVar(value=self.显示行号)
        视图.add_checkbutton(label="显示行号", variable=self.行号变量, command=self.切换行号)
        self.项目变量 = tk.BooleanVar(value=self.显示项目树)
        视图.add_checkbutton(label="项目窗口", variable=self.项目变量, command=self.切换项目树)
        self.对照变量 = tk.BooleanVar(value=self.显示对照表)
        视图.add_checkbutton(label="语法对照表", variable=self.对照变量, command=self.切换对照表)
        self.缩进线变量 = tk.BooleanVar(value=self.显示缩进线)
        视图.add_checkbutton(label="缩进参考线", variable=self.缩进线变量, command=self.切换缩进线)
        菜单栏.add_cascade(label="视图", menu=视图)

        帮助 = tk.Menu(菜单栏, tearoff=0, font=界面字体)
        帮助.add_command(label="语法速查", command=self.显示速查)
        帮助.add_command(label="打开说明文档", command=self.打开说明)
        帮助.add_separator()
        帮助.add_command(label="版本历史", command=self.版本历史)
        帮助.add_separator()
        帮助.add_command(label="关于核工坊", command=self.关于)
        菜单栏.add_cascade(label="帮助", menu=帮助)
        self.主菜单 = 菜单栏
        self.汉堡.bind("<Button-1>", self._弹主菜单)

    def _弹主菜单(self, 事件):
        """点 ≡ 在按钮下方弹出完整菜单（PyCharm 新 UI 的汉堡菜单）。"""
        菜单 = getattr(self, "主菜单", None)
        if 菜单 is None:
            return
        try:
            菜单.tk_popup(事件.x_root, 事件.y_root)
        finally:
            菜单.grab_release()

    def 打开设置(self, _事件=None):
        """打开独立设置弹窗。"""
        try:
            import 设置窗口
        except ImportError as e:
            self.状态("设置窗口不可用：%s" % e)
            return
        窗 = getattr(self, "_设置窗", None)
        if 窗 is not None and 窗.winfo_exists():
            窗.lift()
            窗.focus_force()
            return
        self._设置窗 = 设置窗口.设置窗口(self)
        self.wait_window(self._设置窗)
        if getattr(self._设置窗, "结果", False):
            self.状态("设置已保存")

    # —— 主题 ——

    def 应用主题(self):
        主题 = self.主题
        根 = self.根
        根.configure(bg=主题["窗口"])
        样式 = ttk.Style()
        try:
            样式.theme_use("clam")
        except tk.TclError:
            pass
        样式.configure(
            ".",
            background=主题["面板"],
            foreground=主题["文本"],
            fieldbackground=主题["编辑器"],
            bordercolor=主题["边框"],
            lightcolor=主题["面板"],
            darkcolor=主题["面板"],
            troughcolor=主题["窗口"],
            font=界面字体,
        )
        样式.configure(
            self.树样式名,
            background=主题["面板2"],
            fieldbackground=主题["面板2"],
            foreground=主题["文本"],
            bordercolor=主题["边框"],
            font=界面字体,
            rowheight=22,
        )
        样式.map(
            self.树样式名,
            background=[("selected", 主题["选中行"])],
            foreground=[("selected", "#ffffff")],
        )
        样式.configure(
            "TScrollbar",
            background=主题["按钮"],
            troughcolor=主题["窗口"],
            bordercolor=主题["窗口"],
            arrowcolor=主题["次要文本"],
            relief="flat",
        )
        样式.map("TScrollbar", background=[("active", 主题["按钮热"])])
        样式.configure("TPanedwindow", background=主题["窗口"])
        样式.configure("Sash", sashthickness=5, gripcount=0)
        self.根.option_add("*Menu.background", 主题["面板"])
        self.根.option_add("*Menu.foreground", 主题["文本"])
        self.根.option_add("*Menu.activeBackground", 主题["强调"])
        self.根.option_add("*Menu.activeForeground", "#ffffff")
        for 框 in (self.项目框, self.侧框, self.下框):
            框.configure(bg=主题["面板2"])
        for 框 in (self.编辑框, self.中部, self.主体):
            框.configure(bg=主题["窗口"])
        for 框 in (self.标签栏, self.主工具条, self.左条):
            框.configure(bg=主题["工具条"])
        for 框 in (self.标题栏,):
            框.configure(bg=主题["标题栏"])
        for 框 in (self.输出标题行, self.输入行, self.项目标题, self.侧栏标题):
            框.configure(bg=主题["面板"])
        self.编辑面包屑.configure(bg=主题["面包屑"], fg=主题["面包屑字"])
        self.面包屑.configure(bg=主题["工具条"], fg=主题["面包屑字"])
        self.项目名标.configure(bg=主题["标题栏"], fg=主题["文本"])
        self.品牌图.configure(bg=主题["标题栏"])
        self.汉堡.configure(bg=主题["标题栏"], fg=主题["面包屑字"])
        self.搜索框.configure(
            bg=主题["面板2"], fg=主题["文本"], insertbackground=主题["光标"]
        )
        for 钮 in self.左按钮.values():
            钮.configure(bg=主题["工具条"], fg=主题["面包屑字"])
        for 钮 in getattr(self, "运行钮集", []):
            钮.configure(bg=主题["面板"], fg=主题["面包屑字"])
        self.运行工具条.configure(bg=主题["面板"])
        self.标签栏.configure(bg=主题["工具条"])
        if hasattr(self, "新标签钮"):
            self.新标签钮.configure(bg=主题["工具条"], fg=主题["面包屑字"])
        for 分隔 in (getattr(self, "分隔1", None),):
            if 分隔 is not None:
                分隔.configure(bg=主题["状态栏"], fg=主题["边框"])
        self.欢迎.configure(bg=主题["编辑器"])
        for 子 in self.欢迎.winfo_children():
            子.configure(bg=主题["编辑器"])
            for 孙 in 子.winfo_children():
                孙.configure(bg=主题["编辑器"])
        self.控制台.configure(
            bg=主题["运行条"], fg=主题["控制台字"], insertbackground=主题["光标"]
        )
        self.控制台.tag_configure("错误", foreground=主题["错误"])
        self.控制台.tag_configure("命令", foreground=主题["命令"])
        self.控制台.tag_configure("输入", foreground=主题["输入"])
        self.控制台.tag_configure("提示", foreground=主题["强调"])
        self.对照表.configure(bg=主题["面板2"], fg=主题["文本"])
        self._对照标签()
        self.输入框.configure(
            bg=主题["面板2"],
            fg=主题["文本"],
            disabledbackground=主题["面板2"],
            disabledforeground=主题["次要文本"],
            insertbackground=主题["光标"],
        )
        self.对照搜索.configure(
            bg=主题["编辑器"], fg=主题["文本"], insertbackground=主题["光标"]
        )
        for 条 in (self.状态条,):
            条.configure(bg=主题["状态栏"])
            for 子 in 条.winfo_children():
                子.configure(bg=主题["状态栏"], fg=主题["次要文本"])
        for 钮 in self.按钮集:
            钮.换主题(主题)
        for 行框 in (self.项目标题, self.侧栏标题, self.输出标题行, self.输入行):
            for 孙 in 行框.winfo_children():
                try:
                    孙.configure(bg=主题["面板"])
                except tk.TclError:
                    pass
        self.输入框.configure(
            bg=主题["编辑器"], fg=主题["文本"], insertbackground=主题["光标"]
        )
        for 文档 in self.文档集:
            文档.换主题()
            try:
                文档.文本.tag_configure("缩进线", foreground=主题["缩进线"])
            except tk.TclError:
                pass
        self._刷新标签外观()
        self.输出标题.configure(bg=主题["面板"])
        self.运行状态.configure(bg=主题["面板"], fg=主题["次要文本"])

    def 换主题(self, 名):
        self.主题 = 主题集.get(名, 深色)
        self.应用主题()
        self._填对照表()
        self.状态("已切换到%s主题" % self.主题["名"])
        self.存配置()

    # —— 文档管理 ——

    def 新建(self):
        文档 = 编辑器(self, None)
        文档.置文本("")
        self.文档集.append(文档)
        文档.grid(row=0, column=0, sticky="nsew")
        文档.grid_remove()
        self._建标签(文档)
        self.显示文档(文档)
        return 文档

    def _建标签(self, 文档):
        """圆角标签页：Canvas 画圆角底衬，文字与关闭按钮叠在上面。"""
        主题 = self.主题
        片 = tk.Canvas(
            self.标签栏,
            bg=主题["工具条"],
            highlightthickness=0,
            bd=0,
            height=32,
            cursor="hand2",
        )
        片.pack(side="left", padx=(2, 2), pady=(4, 2))

        名 = tk.Label(
            片,
            text=文档.显示名() if hasattr(文档, "显示名") else self._文档名(文档),
            bg=主题["工具条"],
            fg=主题["次要文本"],
            font=界面字体,
            bd=0,
        )
        关 = tk.Label(
            片,
            text="×",
            bg=主题["工具条"],
            fg=主题["次要文本"],
            font=("Microsoft YaHei UI", 10),
            cursor="hand2",
        )
        文档.标签片 = 片
        文档.标签名 = 名
        文档.关闭钮 = 关
        文档.标签底线 = None
        文档.标签画布 = 片
        self._排标签内容(文档, 选中=False)

        名.bind("<Button-1>", lambda e, d=文档: self.显示文档(d))
        片.bind("<Button-1>", lambda e, d=文档: self.显示文档(d))
        关.bind("<Button-1>", lambda e, d=文档: self.关闭文档(d))
        挂提示(关, "关闭")

    def _排标签内容(self, 文档, 选中=False):
        """按当前文件名计算宽度，重画圆角底衬并摆放文字/关闭按钮。"""
        主题 = self.主题
        片 = 文档.标签画布
        名 = 文档.标签名
        关 = 文档.关闭钮
        文本 = self._文档名(文档)
        名.configure(text=文本)
        测 = tkfont.Font(font=界面字体)
        文字宽 = 测.measure(文本)
        宽 = 文字宽 + 46
        高 = 32
        片.configure(width=宽)

        底 = 主题["编辑器"] if 选中 else 主题["工具条"]
        字 = 主题["文本"] if 选中 else 主题["次要文本"]
        片.configure(bg=主题["工具条"])
        名.configure(bg=底, fg=字)
        关.configure(bg=底, fg=字 if 选中 else 主题["面包屑字"])

        片.delete("all")
        if 选中:
            圆角.圆角矩形(
                片, 0, 0, 宽 - 1, 高 - 1, 主题.get("圆角小", 6) + 3,
                fill=底, outline=""
            )
            # 选中标签的底部高亮条
            片.create_rectangle(
                7, 高 - 3, 宽 - 7, 高 - 1,
                fill=主题["标签选中底线"], outline=""
            )
        名.place(x=11, y=6)
        关.place(x=宽 - 24, y=4)

    def _文档名(self, 文档):
        if 文档.文件路径:
            名 = os.path.basename(文档.文件路径)
        else:
            名 = "未命名"
        名 = 名 + ("*" if 文档.已改 else "")
        return 名

    def 刷新标签(self, 文档):
        选中 = 文档 is self.当前
        self._排标签内容(文档, 选中)
        self._刷新标题()

    def _刷新标签外观(self):
        for 文档 in self.文档集:
            self.刷新标签(文档)

    def _刷新标题(self):
        名 = self._文档名(self.当前) if self.当前 else ""
        名 = 名.rstrip("*")
        self.根.title(
            "%s v%s — %s%s"
            % (
                标题,
                内核.版本,
                名 or "未打开文件",
                " *" if (self.当前 and self.当前.已改) else "",
            )
        )

    def 当前编辑器(self):
        return self.当前

    def 显示文档(self, 文档):
        if 文档 not in self.文档集:
            return
        for d in self.文档集:
            d.grid_remove()
        if getattr(self, "欢迎", None) is not None:
            self.欢迎.grid_remove()
        文档.grid()
        文档.lift()
        文档.文本.focus_set()
        self.当前 = 文档
        self._刷新标签外观()
        self.高亮(文档)
        文档._画行号()
        self.更新状态栏()

    def _显示欢迎(self):
        """回到欢迎页。

        Tk 在「多个文档叠在同一格、逐个销毁」之后不会自动把幸存控件重新
        映射，这里显式 remove + grid 并立刻走一次 idle，保证欢迎页可见。
        """
        欢 = getattr(self, "欢迎", None)
        if 欢 is None:
            return
        欢.grid_remove()
        欢.grid(row=0, column=0, sticky="nsew")
        欢.lift()
        try:
            self.根.update_idletasks()
        except tk.TclError:
            return
        if not 欢.winfo_ismapped():
            欢.grid_remove()
            欢.grid(row=0, column=0, sticky="nsew")

    def 关闭文档(self, 文档, 强制=False):
        if 文档.已改 and not 强制:
            答案 = messagebox.askyesnocancel(
                "保存确认", "“%s”已修改，要保存吗？" % (文档.文件路径 or "未命名"), parent=self.根
            )
            if 答案 is None:
                return False
            if 答案:
                self.保存(文档)
        # 关掉的正是正在运行的那个文件：先停掉，别留下没人管的子进程
        if (
            self.进程 is not None
            and self.进程.poll() is None
            and 文档.文件路径
            and getattr(self, "当前运行文件", None) == 文档.文件路径
        ):
            self.停止()
        索引 = self.文档集.index(文档)
        self.文档集.remove(文档)
        文档.标签片.destroy()
        文档.destroy()
        if self.当前 is 文档:
            self.当前 = None
            if self.文档集:
                下一个 = self.文档集[min(索引, len(self.文档集) - 1)]
                self.显示文档(下一个)
            else:
                self._显示欢迎()
                self._刷新标题()
                self.更新状态栏()
        else:
            self._刷新标签外观()
        return True

    def 关闭当前(self):
        if self.当前:
            self.关闭文档(self.当前)

    # —— 文件操作 ——

    def _初始打开(self):
        for 文档 in list(self.文档集):
            self.关闭文档(文档, 强制=True)
        if not self.显示项目树:
            self._藏项目树()
        if not self.显示对照表:
            self._藏对照表()
        self._装载项目树(self.项目目录)
        参数 = sys.argv[1:]
        目标 = None
        for a in 参数:
            if os.path.isfile(a):
                目标 = a
                break
        if 目标:
            self.打开(目标)
        elif self.最近:
            候选 = self.最近[0]
            if os.path.isfile(候选):
                self.打开(候选)

    def 打开(self, 路径):
        路径 = 规范化路径(路径)
        for 文档 in self.文档集:
            if 文档.文件路径 and 规范化路径(文档.文件路径) == 路径:
                self.显示文档(文档)
                self._加最近(路径)
                return 文档
        if not os.path.isfile(路径):
            # 文件不存在属于可预期的输入错误，不该弹模态框打断用户
            self.状态("文件不存在：%s" % 路径)
            return None
        try:
            内容 = 内核.读源码(路径)
        except OSError as e:
            self.状态("打不开文件：%s" % e)
            return None
        文档 = 编辑器(self, 路径)
        self.文档集.append(文档)
        文档.grid(row=0, column=0, sticky="nsew")
        文档.grid_remove()
        文档.置文本(内容.replace("\r\n", "\n").replace("\r", "\n"))
        self._建标签(文档)
        self.显示文档(文档)
        self._加最近(路径)
        self.状态("已打开 %s" % os.path.basename(路径))
        return 文档

    def 打开文件(self):
        初始 = self.项目目录
        路径 = filedialog.askopenfilename(
            parent=self.根,
            title="打开核语言文件",
            initialdir=初始,
            filetypes=[("核语言源文件", "*.xht"), ("所有文件", "*.*")],
        )
        if 路径:
            self.打开(路径)

    def 打开文件夹(self):
        目录 = filedialog.askdirectory(parent=self.根, title="选择项目文件夹", initialdir=self.项目目录)
        if 目录:
            self.项目目录 = 规范化路径(目录)
            self._装载项目树(self.项目目录)
            self.状态("项目：%s" % self.项目目录)
            self.存配置()

    def 保存(self, 文档=None):
        文档 = 文档 or self.当前
        if 文档 is None:
            return False
        if not 文档.文件路径:
            return self.另存为(文档)
        try:
            with open(文档.文件路径, "w", encoding="utf-8", newline="\n") as f:
                f.write(文档.取文本())
        except OSError as e:
            self.状态("保存失败：%s" % e)
            messagebox.showerror("保存失败", str(e), parent=self.根)
            return False
        文档.已改 = False
        文档.文本.edit_modified(False)
        self.刷新标签(文档)
        self.状态("已保存 %s" % os.path.basename(文档.文件路径))
        return True

    def 另存为(self, 文档=None):
        文档 = 文档 or self.当前
        if 文档 is None:
            return False
        初名 = os.path.basename(文档.文件路径) if 文档.文件路径 else "未命名.xht"
        路径 = filedialog.asksaveasfilename(
            parent=self.根,
            title="另存为",
            initialdir=self.项目目录,
            initialfile=初名,
            defaultextension=".xht",
            filetypes=[("核语言源文件", "*.xht"), ("所有文件", "*.*")],
        )
        if not 路径:
            return False
        文档.文件路径 = 规范化路径(路径)
        ok = self.保存(文档)
        if ok:
            self._加最近(文档.文件路径)
        return ok

    def _加最近(self, 路径):
        路径 = 规范化路径(路径)
        self.最近 = [p for p in self.最近 if p != 路径]
        self.最近.insert(0, 路径)
        self.最近 = self.最近[:12]
        self._填最近菜单()
        self.存配置()

    def _填最近菜单(self):
        菜单 = getattr(self, "最近菜单", None)
        if 菜单 is None:
            return
        菜单.delete(0, "end")
        if not self.最近:
            菜单.add_command(label="（空）", state="disabled")
            return
        for p in self.最近:
            if os.path.isfile(p):
                菜单.add_command(label=p, command=lambda p=p: self.打开(p))
        if not 菜单.index("end"):
            菜单.add_command(label="（空）", state="disabled")

    def 退出(self):
        for 文档 in list(self.文档集):
            if 文档.已改:
                答案 = messagebox.askyesnocancel(
                    "退出确认", "“%s”还没保存，要保存吗？" % (文档.文件路径 or "未命名"), parent=self.根
                )
                if 答案 is None:
                    return
                if 答案 and not self.保存(文档):
                    return
        if self.进程 and self.进程.poll() is None:
            try:
                self.进程.kill()
            except Exception:
                pass
            self._收尾进程(self.进程)
        self.配置.update(
            {
                "主题": self.主题["名"],
                "字号": self.字号,
                "行号": self.显示行号,
                "项目树": self.显示项目树,
                "对照表": self.显示对照表,
                "缩进线": self.显示缩进线,
                "最近": self.最近,
                "项目目录": self.项目目录,
                "窗口尺寸": self._当前尺寸(),
            }
        )
        self._已退出 = True
        存配置(self.配置)
        self.根.destroy()

    # —— 项目树 ——

    def _装载项目树(self, 目录):
        self.树.delete(*self.树.get_children())
        self.项目路径标签.configure(text=os.path.basename(目录) or 目录)
        self.树根 = self.树.insert("", "end", text="  " + (os.path.basename(目录) or 目录), open=True, values=[目录])
        self.树.item(self.树根, image=self.图标["文件夹"])
        self._填目录(self.树根, 目录)
        self.项目目录 = 目录
        if not self.显示项目树:
            self.显示项目树 = True
            self.项目变量.set(True)
            self.项目框.grid()

    def _填目录(self, 节点, 目录):
        try:
            项 = sorted(os.scandir(目录), key=lambda e: (not e.is_dir(), e.name.lower()))
        except OSError:
            return
        for 条 in 项:
            if 条.name.startswith(".") or 条.name in ("__pycache__",):
                continue
            if 条.is_dir():
                子 = self.树.insert(节点, "end", text="  " + 条.name, values=[条.path])
                self.树.item(子, image=self.图标["文件夹"])
                self.树.insert(子, "end", text="…")
            elif 条.name.endswith((".xht", ".py", ".txt", ".md")):
                子 = self.树.insert(节点, "end", text="  " + 条.name, values=[条.path])
                self.树.item(子, image=self.图标["核"] if 条.name.endswith(".xht") else None)

    def _展开节点(self, _e=None):
        节点 = self.树.focus()
        if not 节点:
            return
        子们 = self.树.get_children(节点)
        if len(子们) == 1 and self.树.item(子们[0], "text") == "…":
            self.树.delete(子们[0])
            self._填目录(节点, self.树.item(节点, "values")[0])

    def _双击树(self, _e=None):
        节点 = self.树.focus()
        if not 节点:
            return
        路径 = self.树.item(节点, "values")[0]
        if os.path.isfile(路径):
            self.打开(路径)

    # —— 编辑辅助 ——

    def 全选(self):
        编 = self.当前编辑器()
        if 编:
            编.文本.tag_add("sel", "1.0", "end-1c")
            return "break"

    def 查找替换(self):
        if self.查找窗 is not None and self.查找窗.winfo_exists():
            self.查找窗.lift()
            self.查找窗.查找框.focus_set()
            return
        self.查找窗 = 查找框(self)

    def 转到行(self):
        编 = self.当前编辑器()
        if not 编:
            return
        行 = simple_prompt(self, "转到行", "行号：", "")
        if not 行:
            return
        try:
            n = max(1, min(编.行数(), int(行)))
        except ValueError:
            return
        编.文本.mark_set("insert", "%d.0" % n)
        编.文本.see("%d.0" % n)
        编.文本.focus_set()

    def 注释切换(self):
        编 = self.当前编辑器()
        if not 编:
            return
        文本 = 编.文本
        首 = int(文本.index("insert").split(".")[0])
        if 文本.tag_ranges("sel"):
            起 = int(文本.index("sel.first").split(".")[0])
            止 = int(文本.index("sel.last").split(".")[0])
            if 文本.index("sel.last").split(".")[1] == "0" and 止 > 起:
                止 -= 1
        else:
            起 = 止 = 首
        行集 = [文本.get("%d.0" % i, "%d.end" % i) for i in range(起, 止 + 1)]
        有内容 = [s for s in 行集 if s.strip()]
        if not 有内容:
            return
        全注释 = all(s.lstrip().startswith("核核 ") for s in 有内容)
        for i, s in zip(range(起, 止 + 1), 行集):
            if 全注释:
                新 = s.replace("核核 ", "", 1)
            else:
                if not s.strip():
                    continue
                缩进 = len(s) - len(s.lstrip())
                新 = s[:缩进] + "核核 " + s[缩进:]
            文本.delete("%d.0" % i, "%d.end" % i)
            文本.insert("%d.0" % i, 新)
        编.已改 = True
        self.刷新标签(编)

    def 缩进行(self, 方向):
        编 = self.当前编辑器()
        if not 编:
            return
        文本 = 编.文本
        if 文本.tag_ranges("sel"):
            起 = int(文本.index("sel.first").split(".")[0])
            止 = int(文本.index("sel.last").split(".")[0])
        else:
            起 = 止 = int(文本.index("insert").split(".")[0])
        宽 = " " * self.制表宽
        for i in range(起, 止 + 1):
            行文 = 文本.get("%d.0" % i, "%d.end" % i)
            if 方向 > 0:
                文本.insert("%d.0" % i, 宽)
            else:
                if 行文.startswith(宽):
                    文本.delete("%d.0" % i, "%d.0+%dc" % (i, self.制表宽))
                elif 行文.startswith("\t"):
                    文本.delete("%d.0" % i, "%d.0+1c")
                elif 行文.startswith(" "):
                    数 = min(self.制表宽, len(行文) - len(行文.lstrip(" ")))
                    文本.delete("%d.0" % i, "%d.0+%dc" % (i, 数))

    # —— 高亮 ——

    def 高亮延时(self, 文档):
        if self._高亮任务 is not None:
            try:
                self.根.after_cancel(self._高亮任务)
            except Exception:
                pass
        self._高亮任务 = self.根.after(35, lambda: self.高亮(文档))

    def 高亮(self, 文档=None):
        文档 = 文档 or self.当前
        if 文档 is None:
            return
        self._高亮任务 = None
        文本 = 文档.文本
        内容 = 文本.get("1.0", "end-1c")
        文本.tag_remove("关键字", "1.0", "end")
        for 标签 in ("内置", "方法", "字符串", "数字", "注释", "函数名"):
            文本.tag_remove(标签, "1.0", "end")
        for m in 高亮式.finditer(内容):
            组 = m.lastgroup
            if 组 is None:
                continue
            if 组 == "方法":
                self.文本标(文本, "方法", m.start("方法"), m.end("方法"))
                continue
            self.文本标(文本, 组, m.start(), m.end())
        self._画缩进线(文档)

    def _画缩进线(self, 文档):
        """在编辑器上叠加一层竖线，模拟 PyCharm 的缩进参考线。"""
        if 文档 is None:
            return
        文档.画缩进参考线(self.显示缩进线, self.制表宽, self.主题)

    @staticmethod
    def 文本标(文本, 标签, 起, 止):
        文本.tag_add(标签, "1.0+%dc" % 起, "1.0+%dc" % 止)

    # —— 运行 ——

    def _内核路径(self):
        return os.path.join(这里, "核.py")

    def _已打包(self):
        return bool(getattr(sys, "frozen", False))

    def _运行命令(self, 文件路径):
        """返回运行某个 .xht 的完整命令列表。

        源码运行时：python 核.py 文件.xht
        打包运行时：核工坊.exe --内核 文件.xht  核核 exe 自带内核，不需要装 Python
        """
        if 宿主EXE and os.path.isfile(宿主EXE):
            return [宿主EXE, "--内核", 文件路径]
        return [self._解释器(), self._内核路径(), 文件路径]

    def _解释器(self):
        """源码运行时返回 Python 路径；打包后若需回退，则在机器上找 Python。"""
        if not self._已打包():
            可执行 = sys.executable or "python"
            if os.path.basename(可执行).lower() == "pythonw.exe":
                候选 = os.path.join(os.path.dirname(可执行), "python.exe")
                if os.path.isfile(候选):
                    return 候选
            return 可执行
        # PATH 里可能装着别的 Python（比如 LibreOffice 自带、没有 tkinter），
        # 所以优先用 py 启动器，其次是 PATH 里的 python，最后再逐个探测安装目录。
        for 名 in ("py.exe", "python.exe"):
            路径 = shutil.which(名)
            if 路径:
                return 路径
        for 盘 in ("PROGRAMFILES", "LOCALAPPDATA", "PROGRAMFILES(X86)"):
            基 = os.environ.get(盘)
            if not 基:
                continue
            根 = os.path.join(基, "Programs", "Python")
            if os.path.isdir(根):
                for 子 in sorted(os.listdir(根), reverse=True):
                    候选 = os.path.join(根, 子, "python.exe")
                    if os.path.isfile(候选):
                        return 候选
        for 候选 in (
            r"C:\Python312\python.exe",
            r"C:\Python311\python.exe",
            r"C:\Python310\python.exe",
        ):
            if os.path.isfile(候选):
                return 候选
        return None

    def 运行(self):
        if self.进程 and self.进程.poll() is None:
            self.状态("程序还在运行，先停止它")
            return
        编 = self.当前编辑器()
        if 编 is None:
            self.新建()
            编 = self.当前
        路径 = 编.文件路径
        if not 路径:
            if not self.另存为(编):
                return
            路径 = 编.文件路径
        if 编.已改:
            self.保存(编)
        self.清空控制台()
        if 宿主EXE and os.path.isfile(宿主EXE):
            self._执行(self._运行命令(路径), 路径)
            return
        解释器 = self._解释器()
        if 解释器 is None:
            self.控制台追加(
                "找不到 Python 解释器，无法运行程序。"
                "\n核语言目前基于 Python 3.8+，请先安装 Python 并勾选"
                "\n「Add Python to PATH」，然后重开核工坊。"
                "\n下载：https://www.python.org/downloads/windows/\n",
                "错误",
            )
            self.运行状态.configure(text="未就绪", fg=self.主题["错误"])
            self.状态("缺少 Python 解释器")
            return
        self._执行([解释器, self._内核路径(), 路径], 路径)

    def 检查语法(self):
        编 = self.当前编辑器()
        if 编 is None or not 编.文件路径:
            self.状态("先保存文件，再检查语法")
            return
        if 编.已改:
            self.保存(编)
        源码 = 内核.读源码(编.文件路径)
        报告 = 内核.未定义报告(内核.默认报告路径(编.文件路径))
        try:
            代码, _ = 内核.编译源码(源码, 编.文件路径, 报告)
        finally:
            报告.保存()
        self.输出标题.configure(text="运行")
        self.清空控制台()
        if 代码 is None:
            self.控制台追加("语法检查未通过，见上方提示。\n", "错误")
            self.状态("语法检查未通过")
        else:
            self.控制台追加(
                "语法检查通过：%s\n" % os.path.basename(编.文件路径), "提示"
            )
            if 报告.条数():
                self.控制台追加(
                    "有 %d 条未定义写法已记入 未定义.txt。\n" % 报告.条数(), "提示"
                )
            self.状态("语法检查通过")

    def _执行(self, 命令, 文件路径):
        环境 = dict(os.environ)
        环境["PYTHONIOENCODING"] = "utf-8"
        环境["PYTHONUNBUFFERED"] = "1"
        环境["PYTHONUTF8"] = "1"
        工作目录 = self.项目目录 if os.path.isdir(self.项目目录) else os.path.dirname(文件路径)
        self.控制台追加(
            "> %s\n" % " ".join('"%s"' % c if " " in c else c for c in 命令[1:]), "命令"
        )
        try:
            self.进程 = subprocess.Popen(
                命令,
                cwd=工作目录,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=环境,
            )
        except OSError as e:
            self.控制台追加("启动失败：%s\n" % e, "错误")
            return
        self.运行状态.configure(text="运行中…", fg=self.主题["强调"])
        self.状态("运行 %s" % os.path.basename(文件路径))
        self.输入框.configure(state="normal", bg=self.主题["编辑器"])
        self.输入框.focus_set()
        if hasattr(self, "输入提示"):
            self.输入提示.configure(text="程序在等输入 →", fg=self.主题["强调"])
        self.当前运行文件 = 文件路径
        self.运行标记 += 1
        标记 = self.运行标记

        def 读(进程对象):
            """读子进程输出，做到「有字就立刻显示」。

            不能用 readline / read：提示语（如「请输入：」）常常不带换行，
            阻塞读会一直等到换行或进程结束，界面看起来就像卡死了。
            这里把管道设成非阻塞，小步轮询，读到什么就先送上界面。
            """
            try:
                os.set_blocking(进程对象.stdout.fileno(), False)
            except (AttributeError, OSError, ValueError):
                pass
            缓冲 = b""
            try:
                while True:
                    块 = b""
                    try:
                        块 = 进程对象.stdout.read1(65536)
                    except (BlockingIOError, InterruptedError):
                        块 = b""
                    except (OSError, ValueError):
                        break
                    if 块:
                        缓冲 += 块
                        continue
                    if 缓冲:
                        self.输出队列.put((标记, 缓冲))
                        缓冲 = b""
                    if 进程对象.poll() is not None:
                        break
                    time.sleep(0.03)
            finally:
                if 缓冲:
                    self.输出队列.put((标记, 缓冲))
                self.输出队列.put((标记, None))


        线程 = threading.Thread(target=读, args=(self.进程,), daemon=True)
        线程.start()

    def _轮询输出(self):
        if getattr(self, "_已退出", False):
            return
        try:
            while True:
                标记, 块 = self.输出队列.get_nowait()
                if 块 is None:
                    continue
                if 标记 != self.运行标记:
                    continue
                文本 = 块.decode("utf-8", "replace")
                self.控制台追加(文本)
        except queue.Empty:
            pass
        进程 = self.进程
        if 进程 is not None and 进程.poll() is not None:
            码 = 进程.returncode
            self._收尾进程(进程)
            self.进程 = None
            self.输入框.configure(state="disabled")
            if hasattr(self, "输入提示"):
                self.输入提示.configure(text="输入", fg=self.主题["次要文本"])
            if 码 == 0:
                self.控制台追加("\n[程序结束，返回 0]\n", "命令")
            else:
                self.控制台追加("\n[程序结束，返回 %s]\n" % 码, "错误")
            self.运行状态.configure(text="就绪", fg=self.主题["次要文本"])
            self.状态("运行结束（返回 %s）" % 码)
            self._刷新未定义提示()
        try:
            self._轮询任务 = self.根.after(60, self._轮询输出)
        except tk.TclError:
            # 窗口已经销毁，停止轮询
            self._已退出 = True

    def _收尾进程(self, 进程):
        """关闭子进程的管道，避免句柄泄漏。"""
        if 进程 is None:
            return
        for 流名 in ("stdin", "stdout", "stderr"):
            流 = getattr(进程, 流名, None)
            if 流 is None:
                continue
            try:
                流.close()
            except (OSError, ValueError):
                pass

    def _刷新未定义提示(self):
        路径 = os.path.join(self.项目目录, 内核.未定义文件名)
        if os.path.exists(路径):
            try:
                报告 = 内核.未定义报告(路径)
                条数 = 报告.条数()
            except Exception:
                条数 = 0
            if 条数:
                self.状态("未定义清单里现在有 %d 条记录（运行 → 查看未定义清单）" % 条数)

    def 停止(self):
        if self.进程 and self.进程.poll() is None:
            try:
                self.进程.kill()
            except Exception:
                pass
            self.控制台追加("\n[已停止]\n", "错误")
            self._收尾进程(self.进程)
            self.进程 = None
            self.输入框.configure(state="disabled")
            self.运行状态.configure(text="就绪", fg=self.主题["次要文本"])
            self.状态("已停止")
        else:
            self.状态("当前没有在运行的程序")

    def _发送输入(self, _e=None):
        内容 = self.输入框.get()
        if self.进程 is None or self.进程.poll() is not None:
            self.状态("程序没有在等待输入")
            self.控制台追加("（程序已结束，这句不会发给任何程序）\n", "错误")
            self.输入框.delete(0, "end")
            return
        try:
            self.进程.stdin.write((内容 + "\n").encode("utf-8"))
            self.进程.stdin.flush()
        except Exception as e:  # noqa: BLE001
            self.控制台追加("发送输入失败：%s\n" % e, "错误")
            self.状态("发送失败，程序可能已经结束")
            self.输入框.delete(0, "end")
            return
        self.控制台追加(内容 + "\n", "输入")
        self.输入框.delete(0, "end")

    # —— 控制台 ——

    def 控制台追加(self, 文本, 标签=None):
        控制台 = self.控制台
        控制台.configure(state="normal")
        if 标签:
            控制台.insert("end", 文本, 标签)
        else:
            控制台.insert("end", 文本)
        控制台.see("end")
        控制台.configure(state="disabled")

    def 清空控制台(self):
        self.控制台.configure(state="normal")
        self.控制台.delete("1.0", "end")
        self.控制台.configure(state="disabled")

    def 打开未定义清单(self):
        路径 = os.path.join(self.项目目录, 内核.未定义文件名)
        if os.path.exists(路径):
            self.打开(路径)
        else:
            self.状态("还没有未定义记录：%s" % 路径)

    def 打开说明(self):
        路径 = os.path.join(这里, "说明.md")
        if os.path.exists(路径):
            os.startfile(路径)
        else:
            self.状态("找不到说明.md")

    def 显示速查(self):
        if self.显示对照表:
            self.对照变量.set(False)
            self._藏对照表()
        else:
            self.对照变量.set(True)
            self._显示对照表()

    def 版本历史(self):
        """列出 版本/ 下已归档的所有版本。"""
        根目录 = os.path.dirname(os.path.abspath(__file__))
        版本根 = os.path.join(根目录, "版本")
        if not os.path.isdir(版本根):
            messagebox.showinfo("版本历史", "还没有归档任何版本。", parent=self.根)
            return
        版本们 = sorted(
            (d for d in os.listdir(版本根) if d.startswith("v")),
            key=lambda x: [int(n) for n in x[1:].split(".") if n.isdigit()],
        )
        if not 版本们:
            messagebox.showinfo("版本历史", "还没有归档任何版本。", parent=self.根)
            return
        行 = ["当前版本：v%s" % 内核.版本, "", "已归档 %d 个版本：" % len(版本们), ""]
        for 名 in 版本们:
            信息 = os.path.join(版本根, 名, "版本信息.txt")
            时间 = ""
            if os.path.exists(信息):
                try:
                    with open(信息, encoding="utf-8") as f:
                        for 文 in f:
                            if 文.startswith("归档时间："):
                                时间 = 文.strip().split("：", 1)[1]
                                break
                except OSError:
                    pass
            标记 = " ← 当前" if 名 == "v%s" % 内核.版本 else ""
            行.append("  %s%s" % (名, 标记))
            if 时间:
                行.append("      %s" % 时间)
        messagebox.showinfo("版本历史", "\n".join(行), parent=self.根)

    def 关于(self):
        messagebox.showinfo(
            "关于核工坊",
            "%s %s\n%s\n\n核语言源文件后缀：.xht\n内核：%s\nPython：%s"
            % (标题, 内核.版本, 副标题, os.path.basename(self._内核路径()), sys.version.split()[0]),
            parent=self.根,
        )

    # —— 视图切换 ——

    def 切换行号(self):
        self.显示行号 = bool(self.行号变量.get())
        for 文档 in self.文档集:
            文档.行号画布.configure(width=56 if self.显示行号 else 0)
            文档._画行号()
            文档._当前行()
        self.存配置()

    def 切换项目树(self):
        self.显示项目树 = bool(self.项目变量.get())
        if self.显示项目树:
            self._显示项目树()
        else:
            self._藏项目树()
        self.存配置()

    def _显示项目树(self):
        self.显示项目树 = True
        self.中部.grid_columnconfigure(0, weight=0, minsize=230)
        self.项目框.grid()
        if not hasattr(self, "树根") or not self.树.get_children():
            self._装载项目树(self.项目目录)

    def _藏项目树(self):
        self.显示项目树 = False
        self.项目框.grid_remove()
        self.中部.grid_columnconfigure(0, weight=0, minsize=0)

    def 切换缩进线(self):
        self.显示缩进线 = bool(self.缩进线变量.get())
        if self.当前 is not None:
            self._画缩进线(self.当前)
        self.状态("缩进参考线：%s" % ("开" if self.显示缩进线 else "关"))
        self.存配置()

    def 切换对照表(self):
        self.显示对照表 = bool(self.对照变量.get())
        if self.显示对照表:
            self._显示对照表()
        else:
            self._藏对照表()
        self.存配置()

    def _显示对照表(self):
        self.显示对照表 = True
        self.中部.grid_columnconfigure(2, weight=0, minsize=280)
        self.侧框.grid()

    def _藏对照表(self):
        self.显示对照表 = False
        self.侧框.grid_remove()
        # grid_remove 会保留列宽，必须把 minsize 归零，否则会留下一块空白
        self.中部.grid_columnconfigure(2, weight=0, minsize=0)

    # —— 对照表 ——

    def _填对照表(self):
        表 = getattr(self, "对照表", None)
        if 表 is None:
            return
        关键词 = self.对照搜索.get().strip().lower()
        表.configure(state="normal")
        表.delete("1.0", "end")
        有结果 = False
        for 类别, 映射 in (
            ("关键字", 内核.关键词表),
            ("内置函数", 内核.函数表),
            ("方法", 内核.方法表),
            ("参数名", 内核.参数表),
        ):
            条 = [
                (中, 英)
                for 中, 英 in 映射.items()
                if not 关键词 or 关键词 in 中.lower() or 关键词 in 英.lower()
            ]
            if not 条:
                continue
            有结果 = True
            表.insert("end", 类别 + "（%d）\n" % len(条), "类")
            for 中, 英 in 条:
                宽 = sum(2 if ord(c) > 127 else 1 for c in 中)
                填充 = " " * max(1, 8 - 宽)
                表.insert("end", " " + 中, "中")
                表.insert("end", 填充 + "=  ", "号")
                表.insert("end", 英 + "\n", "英")
            表.insert("end", "\n")
        if not 有结果:
            表.insert("end", "\n没有匹配的写法\n", "说")
        表.configure(state="disabled")

    # —— 状态 ——

    def 状态(self, 文本):
        self.状态信息.configure(text=文本)

    def 更新状态栏(self):
        编 = self.当前编辑器()
        if 编 is None:
            self.位置信息.configure(text="")
            self.面包屑_设("")
            self.编辑面包屑.configure(text="")
            return
        行, 列 = 编.文本.index("insert").split(".")
        try:
            选中 = len(编.文本.get("sel.first", "sel.last"))
        except tk.TclError:
            选中 = 0
        附加 = "  ⧉%d" % 选中 if 选中 else ""
        self.位置信息.configure(text="行 %s，列 %s%s" % (行, int(列) + 1, 附加))
        self.编码信息.configure(text="UTF-8")
        self.缩进信息.configure(text="空格 %d" % self.制表宽)
        self.语言信息.configure(text="核语言")
        self._更新面包屑(编, 行)

    def 面包屑_设(self, 文本):
        标 = getattr(self, "面包屑", None)
        if 标 is not None:
            标.configure(text=文本)

    def _更新面包屑(self, 编, 行):
        """顶部与编辑器上方各一条面包屑：项目 › 文件 › 所在函数。"""
        项目名 = os.path.basename(self.项目目录.rstrip("\\/")) or self.项目目录
        文件名 = os.path.basename(编.文件路径) if 编.文件路径 else "未命名.xht"
        所在 = self._所在函数(编, int(行))
        路径 = "  ›  ".join(x for x in (项目名, 文件名, 所在) if x)
        self.面包屑_设(路径)
        self.编辑面包屑.configure(text="  " + 路径 if 路径 else "")

    @staticmethod
    def _所在函数(编, 行号):
        """向上找最近的 核定义/def 行，得到光标所在的函数名。"""
        for 行 in range(行号, 0, -1):
            文 = 编.文本.get("%d.0" % 行, "%d.end" % 行)
            去空白 = 文.lstrip()
            for 前缀 in ("核定义", "def ", "核类", "class "):
                if 去空白.startswith(前缀):
                    名 = 去空白[len(前缀):].strip()
                    for 符号 in "（(:： ":
                        名 = 名.split(符号)[0]
                    return "%s()" % 名 if 名 else ""
        return ""

    def 存配置(self):
        配置 = dict(self.配置)
        配置.update(
            {
                "主题": self.主题["名"],
                "字号": self.字号,
                "行号": self.显示行号,
                "项目树": self.显示项目树,
                "对照表": self.显示对照表,
                "缩进线": self.显示缩进线,
                "最近": self.最近,
                "项目目录": self.项目目录,
                "窗口尺寸": self._当前尺寸(),
            }
        )
        self.配置 = 配置
        存配置(配置)

    # —— 快捷键 ——

    def _绑快捷键(self):
        根 = self.根
        绑定 = {
            "<Control-n>": lambda e: self.新建(),
            "<Control-o>": lambda e: self.打开文件(),
            "<Control-s>": lambda e: (self.保存(), "break")[1],
            "<Control-Shift-S>": lambda e: self.另存为(),
            "<Control-w>": lambda e: self.关闭当前(),
            "<F5>": lambda e: self.运行(),
            "<Shift-F5>": lambda e: self.停止(),
            "<F9>": lambda e: self.检查语法(),
            "<Control-f>": lambda e: self.查找替换(),
            "<Control-g>": lambda e: self.转到行(),
            "<Control-a>": lambda e: self.全选(),
            "<Control-q>": lambda e: self.退出(),
            "<Control-comma>": lambda e: self.打开设置(),
        }
        for 键, 函数 in 绑定.items():
            根.bind_all(键, 函数)

    def 启动(self):
        self.根.mainloop()


def theme_safe(主题, 键):
    return 主题.get(键, 主题.get("编辑器", "#ffffff"))


class 简单输入框(tk.Toplevel):
    def __init__(self, 主窗, 标题文本, 提示, 初始=""):
        super().__init__(主窗.根)
        self.结果 = None
        self.title(标题文本)
        self.transient(主窗.根)
        self.resizable(False, False)
        主题 = 主窗.主题
        self.configure(bg=主题["面板"])
        框 = tk.Frame(self, bg=主题["面板"], padx=14, pady=12)
        框.pack()
        tk.Label(框, text=提示, bg=主题["面板"], fg=主题["文本"], font=界面字体).pack(anchor="w")
        变量 = tk.StringVar(value=初始)
        self.输入 = tk.Entry(
            框,
            textvariable=变量,
            width=24,
            bg=主题["编辑器"],
            fg=主题["文本"],
            insertbackground=主题["光标"],
            relief="flat",
        )
        self.输入.pack(fill="x", pady=(6, 10), ipady=3)

        def 确定():
            self.结果 = 变量.get()
            self.destroy()

        钮行 = tk.Frame(框, bg=主题["面板"])
        钮行.pack(fill="x")
        for 文本, 命令 in (("确定", 确定), ("取消", self.destroy)):
            tk.Button(
                钮行,
                text=文本,
                command=命令,
                bg=主题["按钮"],
                fg=主题["文本"],
                relief="flat",
                padx=12,
                pady=3,
                font=界面字体,
                bd=0,
                activebackground=主题["按钮热"],
            ).pack(side="right", padx=4)
        self.bind("<Return>", lambda e: 确定())
        self.bind("<Escape>", lambda e: self.destroy())
        self.输入.focus_set()
        self.输入.select_range(0, "end")
        self.wait_window(self)


def simple_prompt(主窗, 标题文本, 提示, 初始):
    框 = 简单输入框(主窗, 标题文本, 提示, 初始)
    return 框.结果


def 启动(参数=None):
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    要打开 = [a for a in (参数 or []) if os.path.isfile(a)]
    # 主窗口启动时会扫描 sys.argv；这里换成显式传入的文件，避免误开别的参数
    sys.argv = [sys.argv[0]] + 要打开
    窗口 = 主窗口()
    窗口.启动()
    return 0


if __name__ == "__main__":
    sys.exit(启动())
