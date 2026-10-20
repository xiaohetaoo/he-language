# -*- coding: utf-8 -*-
"""核工坊 设置弹窗。

独立窗口，左侧分类、右侧选项，底部确定/取消/应用。
只依赖标准库 tkinter，圆角与配色跟随当前主题。
"""

import os
import tkinter as tk

from 圆角 import 圆角矩形

界面字体 = ("Microsoft YaHei UI", 9)


class 设置窗口(tk.Toplevel):
    """设置面板。

    用法：
        窗 = 设置窗口(主窗)
        主窗.wait_window(窗)
    主窗需提供：主题、字号、显示行号、显示缩进线、显示项目树、显示对照表、
                制表宽、项目目录、换主题()、改字号() 等。
    """

    分类集 = ("外观", "编辑器", "运行", "关于")

    def __init__(self, 主窗):
        super().__init__(主窗.根)
        self.主窗 = 主窗
        self.主题 = 主窗.主题
        self.title("设置")
        self.transient(主窗.根)
        self.resizable(False, False)
        self.configure(bg=self.主题["窗口"])
        self.结果 = False
        # 打开时的原始值，用于「取消」还原
        self.原始 = {
            "主题": 主窗.主题["名"],
            "字号": 主窗.字号,
        }

        # 待提交的设置副本
        self.值 = {
            "主题": self.主题["名"],
            "字号": 主窗.字号,
            "行号": 主窗.显示行号,
            "缩进线": 主窗.显示缩进线,
            "项目树": 主窗.显示项目树,
            "对照表": 主窗.显示对照表,
            "制表宽": 主窗.制表宽,
            "自动高亮": getattr(主窗, "自动高亮", True),
            "运行后清空": getattr(主窗, "运行前清空", True),
            "项目目录": 主窗.项目目录,
        }
        self._建界面()
        self._切分类("外观")
        self._居中()
        self.bind("<Escape>", lambda e: self.destroy())
        self.协议()

    # —— 结构 ——

    def 协议(self):
        self.protocol("WM_DELETE_WINDOW", self.取消)

    def 销毁(self):
        """清理内部菜单等资源后销毁，避免留下 Tcl 命令引用。"""
        try:
            for 子 in self.winfo_children():
                try:
                    子.destroy()
                except Exception:
                    pass
        finally:
            try:
                super().destroy()
            except Exception:
                pass

    def _居中(self):
        self.update_idletasks()
        宽 = self.winfo_width()
        高 = self.winfo_height()
        根 = self.主窗.根
        x = 根.winfo_rootx() + (根.winfo_width() - 宽) // 2
        y = 根.winfo_rooty() + (根.winfo_height() - 高) // 2
        self.geometry("+%d+%d" % (max(0, x), max(0, y)))

    def _建界面(self):
        主题 = self.主题
        主体 = tk.Frame(self, bg=主题["窗口"])
        主体.pack(fill="both", expand=True)

        # 左侧分类
        左 = tk.Frame(主体, bg=主题["面板2"], width=132)
        左.pack(side="left", fill="y")
        左.pack_propagate(False)
        tk.Label(
            左,
            text="设置",
            bg=主题["面板2"],
            fg=主题["文本"],
            font=("Microsoft YaHei UI", 12, "bold"),
            anchor="w",
            padx=14,
            pady=14,
        ).pack(fill="x")

        self.分类按钮 = {}
        for 名 in self.分类集:
            钮 = tk.Label(
                左,
                text="   " + 名,
                bg=主题["面板2"],
                fg=主题["次要文本"],
                font=界面字体,
                anchor="w",
                padx=10,
                pady=8,
                cursor="hand2",
            )
            钮.pack(fill="x")
            钮.bind("<Button-1>", lambda e, n=名: self._切分类(n))
            self.分类按钮[名] = 钮

        # 右侧内容区
        右 = tk.Frame(主体, bg=主题["窗口"], width=380)
        右.pack(side="left", fill="both", expand=True)
        self.内容 = tk.Frame(右, bg=主题["窗口"])
        self.内容.pack(fill="both", expand=True, padx=20, pady=16)

        # 底部按钮
        底 = tk.Frame(self, bg=主题["面板"])
        底.pack(fill="x", side="bottom")
        tk.Frame(底, bg=主题["边框"], height=1).pack(fill="x", side="top")
        行 = tk.Frame(底, bg=主题["面板"])
        行.pack(fill="x", padx=14, pady=10)

        for 文本, 命令 in (("取消", self.取消), ("应用", self.应用), ("确定", self.确定)):
            钮 = tk.Button(
                行,
                text=文本,
                command=命令,
                bg=主题["按钮"] if 文本 != "确定" else 主题["强调"],
                fg=主题["文本"] if 文本 != "确定" else "#ffffff",
                activebackground=主题["按钮热"],
                activeforeground=主题["文本"] if 文本 != "确定" else "#ffffff",
                relief="flat",
                bd=0,
                padx=18,
                pady=5,
                font=界面字体,
                cursor="hand2",
            )
            钮.pack(side="right", padx=5)
            if 文本 == "确定":
                self.确定钮 = 钮

    def _切分类(self, 名):
        主题 = self.主题
        for 键, 钮 in self.分类按钮.items():
            选中 = 键 == 名
            钮.configure(
                bg=主题["面板"] if 选中 else 主题["面板2"],
                fg=主题["文本"] if 选中 else 主题["次要文本"],
            )
        for 子 in self.内容.winfo_children():
            子.destroy()
        getattr(self, "_页" + 名)()

    # —— 各分类页面 ——

    def _标题(self, 文本, 说明=""):
        主题 = self.主题
        tk.Label(
            self.内容,
            text=文本,
            bg=主题["窗口"],
            fg=主题["文本"],
            font=("Microsoft YaHei UI", 11, "bold"),
            anchor="w",
        ).pack(fill="x")
        if 说明:
            tk.Label(
                self.内容,
                text=说明,
                bg=主题["窗口"],
                fg=主题["次要文本"],
                font=界面字体,
                anchor="w",
                justify="left",
                wraplength=340,
            ).pack(fill="x", pady=(2, 12))
        else:
            tk.Frame(self.内容, bg=主题["窗口"], height=10).pack(fill="x")

    def _分组(self, 文本):
        主题 = self.主题
        tk.Label(
            self.内容,
            text=文本,
            bg=主题["窗口"],
            fg=主题["次要文本"],
            font=("Microsoft YaHei UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(10, 4))

    def _勾选(self, 文本, 键, 说明=None):
        """自绘勾选框：原生 Checkbutton 在高 DPI 下太小且配色跟随系统。"""
        主题 = self.主题
        变量 = tk.BooleanVar(value=bool(self.值[键]))
        self._变量[键] = 变量
        行 = tk.Frame(self.内容, bg=主题["窗口"])
        行.pack(fill="x", pady=2)
        方 = tk.Canvas(
            行, width=16, height=16, bg=主题["窗口"], highlightthickness=0, bd=0, cursor="hand2"
        )
        方.pack(side="left")
        标 = tk.Label(
            行,
            text=文本,
            bg=主题["窗口"],
            fg=主题["文本"],
            font=界面字体,
            anchor="w",
            cursor="hand2",
        )
        标.pack(side="left", padx=(7, 0))

        def 重画():
            方.delete("all")
            圆角矩形(
                方, 1, 1, 15, 15, 4,
                fill=主题["强调"] if 变量.get() else 主题["面板2"],
                outline=主题["边框"] if not 变量.get() else 主题["强调"],
            )
            if 变量.get():
                方.create_line(4, 8, 7, 11, 12, 5, fill="#ffffff", width=2)

        def 切换(_e=None):
            变量.set(not 变量.get())
            重画()

        方.bind("<Button-1>", 切换)
        标.bind("<Button-1>", 切换)
        重画()
        if 说明:
            tk.Label(
                self.内容,
                text="    " + 说明,
                bg=主题["窗口"],
                fg=主题["次要文本"],
                font=("Microsoft YaHei UI", 8),
                anchor="w",
            ).pack(fill="x")

    def _页外观(self):
        主题 = self.主题
        self._变量 = {}
        self._标题("外观", "主题与界面元素。改动立即在预览中生效。")

        self._分组("配色")
        行 = tk.Frame(self.内容, bg=主题["窗口"])
        行.pack(fill="x", pady=2)
        for 名, 色 in (("深色", "#1e1f22"), ("浅色", "#ffffff")):
            卡 = tk.Frame(
                行,
                bg=主题["强调"] if self.值["主题"] == 名 else 主题["边框"],
                padx=2,
                pady=2,
            )
            卡.pack(side="left", padx=(0, 8))
            内 = tk.Frame(卡, bg=色, width=84, height=52)
            内.pack()
            内.pack_propagate(False)
            tk.Label(
                内,
                text=名,
                bg=色,
                fg="#dfe1e5" if 名 == "深色" else "#1f2329",
                font=界面字体,
            ).pack(expand=True)
            内.bind("<Button-1>", lambda e, n=名: self._选主题(n))
            self.值["_主题卡_" + 名] = 卡

        self._分组("字号")
        字号行 = tk.Frame(self.内容, bg=主题["窗口"])
        字号行.pack(fill="x", pady=2)

        def 步进(差):
            n = max(9, min(22, self.值["字号"] + 差))
            if n != self.值["字号"]:
                self.值["字号"] = n
                self.字号标.configure(text="%d pt" % n)
                self.主窗.改字号(n - self.主窗.字号, 存配置=False)

        for 字, 差, 提示 in (("−", -1, "减小"), ("＋", 1, "增大")):
            钮 = tk.Label(
                字号行,
                text=字,
                bg=主题["按钮"],
                fg=主题["文本"],
                font=("Microsoft YaHei UI", 11, "bold"),
                width=3,
                pady=3,
                cursor="hand2",
            )
            钮.pack(side="left" if 差 < 0 else "right", padx=0)
            钮.bind("<Button-1>", lambda e, d=差: 步进(d))
        self.字号标 = tk.Label(
            字号行,
            text="%d pt" % self.值["字号"],
            bg=主题["窗口"],
            fg=主题["文本"],
            font=界面字体,
        )
        self.字号标.pack(side="left", expand=True)
        tk.Label(
            self.内容,
            text="    编辑器与输出窗口的等宽字号",
            bg=主题["窗口"],
            fg=主题["次要文本"],
            font=("Microsoft YaHei UI", 8),
            anchor="w",
        ).pack(fill="x")

        self._分组("界面元素")
        self._勾选("显示行号", "行号")
        self._勾选("显示缩进参考线", "缩进线", "在缩进处画淡竖线，便于看清层级")
        self._勾选("显示项目侧栏", "项目树")
        self._勾选("显示语法对照表", "对照表", "右侧常驻的中英文对照")

    def _选主题(self, 名):
        self.值["主题"] = 名
        self.主窗.换主题(名)
        self.主题 = self.主窗.主题
        self._重建()

    def _改字号(self, 值):
        try:
            n = int(float(值))
        except (TypeError, ValueError):
            return
        if n == self.值["字号"]:
            return
        self.值["字号"] = n
        self.字号标.configure(text="%d pt" % n)
        self.主窗.改字号(n - self.主窗.字号, 存配置=False)

    def _页编辑器(self):
        主题 = self.主题
        self._变量 = {}
        self._标题("编辑器", "缩进与编辑行为。")

        self._分组("缩进")
        行 = tk.Frame(self.内容, bg=主题["窗口"])
        行.pack(fill="x", pady=2)
        tk.Label(
            行, text="每级缩进空格数", bg=主题["窗口"], fg=主题["文本"], font=界面字体
        ).pack(side="left")
        # 自绘下拉：原生 Combobox 在高 DPI 下是白底，与深色主题不搭
        self.缩进值标 = tk.Label(
            行,
            text="%d 空格" % self.值["制表宽"],
            bg=主题["面板2"],
            fg=主题["文本"],
            font=界面字体,
            padx=10,
            pady=3,
            cursor="hand2",
        )
        self.缩进值标.pack(side="right")
        菜单 = tk.Menu(self, tearoff=0, bg=主题["面板"], fg=主题["文本"], font=界面字体)

        def 选(值):
            self.值["制表宽"] = int(值)
            self.缩进值标.configure(text="%s 空格" % 值)

        for 值 in ("2", "3", "4", "8"):
            菜单.add_command(label="%s 空格" % 值, command=lambda v=值: 选(v))

        def 弹出(_e=None):
            try:
                菜单.tk_popup(
                    self.缩进值标.winfo_rootx(),
                    self.缩进值标.winfo_rooty() + self.缩进值标.winfo_height(),
                )
            finally:
                菜单.grab_release()

        self.缩进值标.bind("<Button-1>", 弹出)

        self._分组("行为")
        self._勾选("输入时自动语法高亮", "自动高亮")
        self._勾选("运行前清空输出窗口", "运行后清空")

    def _改制表宽(self, 值):
        try:
            self.值["制表宽"] = int(值)
        except (TypeError, ValueError):
            pass

    def _页运行(self):
        主题 = self.主题
        self._变量 = {}
        self._标题("运行", "项目位置与运行环境。")

        self._分组("项目目录")
        框 = tk.Frame(self.内容, bg=主题["窗口"])
        框.pack(fill="x")
        路 = tk.Entry(
            框,
            bg=主题["面板2"],
            fg=主题["文本"],
            insertbackground=主题["光标"],
            relief="flat",
            font=界面字体,
        )
        路.insert(0, self.值["项目目录"])
        路.configure(state="readonly", readonlybackground=主题["面板2"])
        路.pack(side="left", fill="x", expand=True, ipady=4)
        tk.Button(
            框,
            text="更改…",
            command=self._选目录,
            bg=主题["按钮"],
            fg=主题["文本"],
            relief="flat",
            bd=0,
            padx=10,
            font=界面字体,
        ).pack(side="left", padx=(6, 0))

        self._分组("解释器")
        import 核 as 内核

        tk.Label(
            self.内容,
            text="%s %s · Python %s" % (内核.程序名, 内核.版本, __import__("sys").version.split()[0]),
            bg=主题["窗口"],
            fg=主题["次要文本"],
            font=界面字体,
            anchor="w",
        ).pack(fill="x")

    def _选目录(self):
        from tkinter import filedialog

        目录 = filedialog.askdirectory(
            parent=self, title="选择项目文件夹", initialdir=self.值["项目目录"]
        )
        if 目录:
            self.值["项目目录"] = os.path.normpath(目录)
            self._切分类("运行")

    def _页关于(self):
        主题 = self.主题
        self._变量 = {}
        self._标题("关于", "")

        import 核 as 内核

        框 = tk.Frame(self.内容, bg=主题["窗口"])
        框.pack(fill="x", pady=(4, 0))
        tk.Label(
            框,
            text="核语言 %s" % 内核.版本,
            bg=主题["窗口"],
            fg=主题["文本"],
            font=("Microsoft YaHei UI", 13, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            框,
            text="用中文写程序 · 源文件后缀 %s" % 内核.扩展名,
            bg=主题["窗口"],
            fg=主题["次要文本"],
            font=界面字体,
            anchor="w",
        ).pack(fill="x", pady=(2, 12))

        for 名, 值 in (
            ("关键字", len(内核.关键词表)),
            ("内置函数", len(内核.函数表)),
            ("方法", len(内核.方法表)),
            ("关键字参数", len(内核.参数表)),
        ):
            行 = tk.Frame(self.内容, bg=主题["窗口"])
            行.pack(fill="x", pady=1)
            tk.Label(
                行, text=名, bg=主题["窗口"], fg=主题["次要文本"], font=界面字体, anchor="w", width=12
            ).pack(side="left")
            tk.Label(
                行, text=str(值), bg=主题["窗口"], fg=主题["文本"], font=界面字体, anchor="w"
            ).pack(side="left")

        tk.Label(
            self.内容,
            text="\n帮助 → 版本历史 可查看每个已归档版本。",
            bg=主题["窗口"],
            fg=主题["次要文本"],
            font=("Microsoft YaHei UI", 8),
            anchor="w",
            justify="left",
        ).pack(fill="x", pady=(12, 0))

    def _重建(self):
        self.主题 = self.主窗.主题
        主题 = self.主题
        self.configure(bg=主题["窗口"])
        for 子 in self.winfo_children():
            子.destroy()
        self._建界面()
        self._切分类("外观")

    # —— 提交 ——

    def _收集(self):
        for 键, 变量 in getattr(self, "_变量", {}).items():
            self.值[键] = bool(变量.get())

    def 应用(self):
        self._收集()
        主窗 = self.主窗
        # 主题与字号在交互时已即时生效，这里同步其余项
        if self.值["行号"] != 主窗.显示行号:
            主窗.行号变量.set(self.值["行号"])
            主窗.切换行号()
        if self.值["缩进线"] != 主窗.显示缩进线:
            主窗.缩进线变量.set(self.值["缩进线"])
            主窗.切换缩进线()
        if self.值["项目树"] != 主窗.显示项目树:
            主窗.项目变量.set(self.值["项目树"])
            主窗.切换项目树()
        if self.值["对照表"] != 主窗.显示对照表:
            主窗.对照变量.set(self.值["对照表"])
            主窗.切换对照表()
        主窗.制表宽 = max(1, int(self.值["制表宽"]))
        主窗.自动高亮 = bool(self.值["自动高亮"])
        主窗.运行前清空 = bool(self.值["运行后清空"])
        if self.值["项目目录"] and self.值["项目目录"] != 主窗.项目目录:
            主窗.项目目录 = self.值["项目目录"]
            主窗._装载项目树(主窗.项目目录)
        主窗.存配置()
        主窗.状态("设置已应用")

    def 确定(self):
        self.应用()
        self.结果 = True
        self.destroy()

    def 取消(self):
        """主题与字号是即时预览的，取消时还原到打开设置前的状态。"""
        主窗 = self.主窗
        if self.主题["名"] != self.原始["主题"]:
            主窗.换主题(self.原始["主题"])
            self.主题 = 主窗.主题
        差 = self.原始["字号"] - 主窗.字号
        if 差:
            主窗.改字号(差, 存配置=False)
        self.结果 = False
        self.destroy()
