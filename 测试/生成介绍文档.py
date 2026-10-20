# -*- coding: utf-8 -*-
"""生成《核语言介绍》Word 文档。"""

import os

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

这里 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 项目根目录

正文体 = "微软雅黑"
代码体 = "Consolas"
标题色 = RGBColor(0x1F, 0x3A, 0x5F)
强调色 = RGBColor(0x0B, 0x63, 0x8A)
灰字 = RGBColor(0x60, 0x60, 0x60)


# ---------------------------------------------------------------------------
# 基础排版工具
# ---------------------------------------------------------------------------


def 设置字体(片段, 字体名, 字号=None, 加粗=None, 颜色=None):
    片段.font.name = 字体名
    片段._element.rPr.rFonts.set(qn("w:eastAsia"), 字体名)
    if 字号 is not None:
        片段.font.size = Pt(字号)
    if 加粗 is not None:
        片段.font.bold = 加粗
    if 颜色 is not None:
        片段.font.color.rgb = 颜色


def 正文(文档, 文本, 字号=10.5, 加粗=False, 颜色=None, 首行缩进=False, 段前=0, 段后=5):
    段 = 文档.add_paragraph()
    段.paragraph_format.space_before = Pt(段前)
    段.paragraph_format.space_after = Pt(段后)
    段.paragraph_format.line_spacing = 1.32
    if 首行缩进:
        段.paragraph_format.first_line_indent = Pt(字号 * 2)
    片段 = 段.add_run(文本)
    设置字体(片段, 正文体, 字号, 加粗, 颜色)
    return 段


def 标题(文档, 文本, 级别=1):
    段 = 文档.add_paragraph()
    if 级别 == 1:
        段.paragraph_format.space_before = Pt(16)
        段.paragraph_format.space_after = Pt(6)
        片段 = 段.add_run(文本)
        设置字体(片段, 正文体, 15, True, 标题色)
    elif 级别 == 2:
        段.paragraph_format.space_before = Pt(10)
        段.paragraph_format.space_after = Pt(4)
        片段 = 段.add_run(文本)
        设置字体(片段, 正文体, 12, True, 强调色)
    else:
        段.paragraph_format.space_before = Pt(6)
        段.paragraph_format.space_after = Pt(2)
        片段 = 段.add_run(文本)
        设置字体(片段, 正文体, 10.5, True, 标题色)
    # 让标题进导航窗格
    段.paragraph_format.keep_with_next = True
    return 段


def _底纹(元素, 颜色):
    属性 = OxmlElement("w:shd")
    属性.set(qn("w:val"), "clear")
    属性.set(qn("w:color"), "auto")
    属性.set(qn("w:fill"), 颜色)
    元素.append(属性)


def 代码块(文档, 代码, 说明=None, 尾空=True):
    """灰底等宽代码块，左侧加一条深色竖线。"""
    if 说明:
        段 = 文档.add_paragraph()
        段.paragraph_format.space_before = Pt(6)
        段.paragraph_format.space_after = Pt(2)
        段.paragraph_format.keep_with_next = True
        片段 = 段.add_run(说明)
        设置字体(片段, 正文体, 9, False, 灰字)

    for 行 in 代码.split("\n"):
        段 = 文档.add_paragraph()
        段.paragraph_format.space_before = Pt(0)
        段.paragraph_format.space_after = Pt(0)
        段.paragraph_format.line_spacing = 1.05
        段.paragraph_format.left_indent = Cm(0.45)
        段.paragraph_format.keep_with_next = True
        片段 = 段.add_run(行 if 行 else " ")
        设置字体(片段, 代码体, 9.0)

        段属性 = 段._p.get_or_add_pPr()
        _底纹(段属性, "F2F4F7")
        边框 = OxmlElement("w:pBdr")
        左 = OxmlElement("w:left")
        左.set(qn("w:val"), "single")
        左.set(qn("w:sz"), "18")
        左.set(qn("w:space"), "6")
        左.set(qn("w:color"), "4A88C7")
        边框.append(左)
        段属性.append(边框)

    # 代码块后留白（可省略，用于减少分页）
    if 尾空:
        尾 = 文档.add_paragraph()
        尾.paragraph_format.space_before = Pt(0)
        尾.paragraph_format.space_after = Pt(0)
        尾.paragraph_format.line_spacing = 0.6


def 要点(文档, 文本, 加粗前段=None):
    段 = 文档.add_paragraph()
    段.paragraph_format.left_indent = Cm(0.75)
    段.paragraph_format.space_before = Pt(0)
    段.paragraph_format.space_after = Pt(3)
    段.paragraph_format.line_spacing = 1.28
    圆 = 段.add_run("•  ")
    设置字体(圆, 正文体, 10.5, False, 强调色)
    if 加粗前段:
        头 = 段.add_run(加粗前段)
        设置字体(头, 正文体, 10.5, True)
    尾 = 段.add_run(文本)
    设置字体(尾, 正文体, 10.5)
    return 段


def 表格(文档, 表头, 行集, 列宽=None, 字号=9.5):
    表 = 文档.add_table(rows=1, cols=len(表头))
    表.style = "Table Grid"
    表.alignment = WD_TABLE_ALIGNMENT.CENTER
    表.autofit = False

    头行 = 表.rows[0]
    for 序, 名 in enumerate(表头):
        格 = 头行.cells[序]
        格.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        段 = 格.paragraphs[0]
        段.alignment = WD_ALIGN_PARAGRAPH.CENTER
        段.paragraph_format.space_before = Pt(2)
        段.paragraph_format.space_after = Pt(2)
        片段 = 段.add_run(名)
        设置字体(片段, 正文体, 字号, True, RGBColor(0xFF, 0xFF, 0xFF))
        _底纹(格._tc.get_or_add_tcPr(), "3C6E9E")

    for 序, 行 in enumerate(行集):
        cells = 表.add_row().cells
        for 列, 值 in enumerate(行):
            格 = cells[列]
            格.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            段 = 格.paragraphs[0]
            段.paragraph_format.space_before = Pt(2)
            段.paragraph_format.space_after = Pt(2)
            片段 = 段.add_run(str(值))
            if 列 == 0:
                设置字体(片段, 代码体, 字号, True)
            else:
                设置字体(片段, 正文体 if 列 != 1 else 代码体, 字号)
            if 序 % 2 == 1:
                _底纹(格._tc.get_or_add_tcPr(), "F5F7FA")

    if 列宽:
        for 序, 宽 in enumerate(列宽):
            for 行 in 表.rows:
                行.cells[序].width = Cm(宽)

    # 表后留白
    尾 = 文档.add_paragraph()
    尾.paragraph_format.space_before = Pt(0)
    尾.paragraph_format.space_after = Pt(0)
    尾.paragraph_format.line_spacing = 0.6
    return 表


def 插图(文档, 路径, 图注, 宽=Cm(16.2), 分页=False):
    """插入居中图片 + 图注。

    图片与图注必须留在同一页：把图片段落设成「与下段同页」，
    并禁止段落内部断开，避免 LibreOffice/Word 把图注甩到下一页。
    """
    if not os.path.exists(路径):
        raise FileNotFoundError("插图缺失：%s" % 路径)
    if 分页:
        断 = 文档.add_paragraph()
        断.paragraph_format.space_before = Pt(0)
        断.paragraph_format.space_after = Pt(0)
        断.paragraph_format.line_spacing = 1.0
        断.add_run().add_break(WD_BREAK.PAGE)
    段 = 文档.add_paragraph()
    段.alignment = WD_ALIGN_PARAGRAPH.CENTER
    段.paragraph_format.space_before = Pt(10)
    段.paragraph_format.space_after = Pt(3)
    段.paragraph_format.keep_with_next = True
    段.paragraph_format.keep_together = True
    段.paragraph_format.line_spacing = 1.0
    段.add_run().add_picture(路径, width=宽)

    注 = 文档.add_paragraph()
    注.alignment = WD_ALIGN_PARAGRAPH.CENTER
    注.paragraph_format.space_before = Pt(0)
    注.paragraph_format.space_after = Pt(14)
    注.paragraph_format.keep_together = True
    注.paragraph_format.line_spacing = 1.0
    片段 = 注.add_run(图注)
    设置字体(片段, 正文体, 8.5, False, 灰字)


def 分隔线(文档):
    段 = 文档.add_paragraph()
    段.paragraph_format.space_before = Pt(6)
    段.paragraph_format.space_after = Pt(6)
    段属性 = 段._p.get_or_add_pPr()
    边框 = OxmlElement("w:pBdr")
    下 = OxmlElement("w:bottom")
    下.set(qn("w:val"), "single")
    下.set(qn("w:sz"), "6")
    下.set(qn("w:space"), "1")
    下.set(qn("w:color"), "C9D3DE")
    边框.append(下)
    段属性.append(边框)


def 页脚(节, 文本):
    段 = 节.footer.paragraphs[0]
    段.alignment = WD_ALIGN_PARAGRAPH.CENTER
    片段 = 段.add_run(文本)
    设置字体(片段, 正文体, 8, False, 灰字)


# ---------------------------------------------------------------------------
# 文档
# ---------------------------------------------------------------------------


def 建文档():
    文档 = Document()

    节 = 文档.sections[0]
    节.page_height = Cm(29.7)
    节.page_width = Cm(21.0)
    节.top_margin = Cm(2.2)
    节.bottom_margin = Cm(2.0)
    节.left_margin = Cm(2.4)
    节.right_margin = Cm(2.4)
    页脚(节, "核语言 0.0.1    用中文写程序")

     # 默认样式也设成雅黑，避免表格里漏掉
    for 样式名 in ("Normal", "Table Grid"):
        try:
            样式 = 文档.styles[样式名]
            样式.font.name = 正文体
            样式.font.size = Pt(10.5)
            样式.element.rPr.rFonts.set(qn("w:eastAsia"), 正文体)
        except Exception:
            pass

    # —— 封面区 ——
    空 = 文档.add_paragraph()
    空.paragraph_format.space_after = Pt(40)

    标 = 文档.add_paragraph()
    标.alignment = WD_ALIGN_PARAGRAPH.CENTER
    标.paragraph_format.space_after = Pt(4)
    片段 = 标.add_run("核 语 言")
    设置字体(片段, 正文体, 30, True, 标题色)

    副 = 文档.add_paragraph()
    副.alignment = WD_ALIGN_PARAGRAPH.CENTER
    副.paragraph_format.space_after = Pt(2)
    片段 = 副.add_run("一门用中文写程序的语言")
    设置字体(片段, 正文体, 13, False, 强调色)

    版 = 文档.add_paragraph()
    版.alignment = WD_ALIGN_PARAGRAPH.CENTER
    版.paragraph_format.space_after = Pt(18)
    片段 = 版.add_run("版本 0.0.1    ·    源文件后缀 .xht    ·    图形界面「核工坊」")
    设置字体(片段, 正文体, 9, False, 灰字)

    插图(
        文档,
        os.path.join(这里, "素材", "核图标.png"),
        "核语言图标：原子轨道与彩色立方体",
        宽=Cm(5.2),
        分页=False,
    )

    分隔线(文档)

    # —— 一句话介绍 ——
    段 = 文档.add_paragraph()
    段.alignment = WD_ALIGN_PARAGRAPH.CENTER
    段.paragraph_format.space_before = Pt(8)
    段.paragraph_format.space_after = Pt(8)
    片段 = 段.add_run("核说（“你好，世界！”）")
    设置字体(片段, 代码体, 12, True, 强调色)

    正文(
        文档,
        "核语言把 Python 的写法换成中文：关键字、内置函数、字符串方法、"
        "关键字参数都有对应的中文名，中英文标点视同，变量名可以直接用汉字。"
        "它不是另起炉灶的新解释器，而是把 .xht 源码转译成 Python 后执行，"
        "所以语义稳、上手快；同时把对照表里没有的写法原样保留并记入清单，"
        "方便一门语言慢慢长大。",
        首行缩进=True,
        段前=4,
    )

    文档.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    # —— 一、快速上手 ——
    标题(文档, "一、五分钟上手", 1)
    正文(
        文档,
        "安装 Python 3.8 或更高版本（Windows 上建议同时勾选 Add Python to PATH），"
        "把本项目文件夹放到任意位置，然后有三种用法：",
        首行缩进=True,
    )
    表格(
        文档,
        ["方式", "怎么做", "适合"],
        [
            ["图形界面", "双击 核工坊.cmd，或执行  核 工坊", "写代码、看输出、查对照表"],
            ["命令行", "核 例子/01_你好.xht", "快速跑一个脚本"],
            ["交互模式", "直接输入  核  ，退出输入 核退出", "试语法、算小结果"],
        ],
        列宽=[3.0, 8.4, 5.0],
    )

    正文(文档, "第一个程序：", 段前=6, 段后=2)
    代码块(
        文档,
        '核核 第一个核程序\n'
        '名字 = 说核（"你叫什么名字？"）\n'
        '核说（"你好，" + 名字 + "！"）\n'
        '核用 i 遍历 核数列（1, 4）：\n'
        '    核说（i, "的平方是", i * i）',
    )
    正文(
        文档,
        "注意上面用的是全角括号和全角逗号，这在核语言里完全合法——"
        "中文输入法状态下不用来回切换。",
        首行缩进=True,
    )

    # —— 二、设计取舍 ——
    标题(文档, "二、设计取舍：为什么是转译", 1)
    正文(
        文档,
        "做一门中文编程语言，通常有两条路：自己写词法分析、语法树和虚拟机，"
        "或者借用一门成熟语言的运行时。核语言选了后者，理由有三个。",
        首行缩进=True,
    )
    要点(文档, "语义不用重新发明。整数除法、字典顺序、异常传播这些细节，"
                "Python 已经打磨了三十多年，直接继承最省事。", "稳。")
    要点(文档, "第一版就能写完整个程序，不必先造一遍标准库。", "快。")
    要点(文档, "转译只做等长替换，行号严格不变，出错时报的「第几行」"
                "就是 .xht 原文的行号，调试体验不打折。", "可调试。")

    正文(
        文档,
        "代价是目标机器需要 Python 运行时。这一点通过打包成 exe 解决："
        "exe 内置了内核，运行用户程序时调用自己，目标机器不需要安装 Python。",
        首行缩进=True,
    )

    # —— 三、语法对照 ——
    标题(文档, "三、语法对照表", 1)
    正文(
        文档,
        "下面这些是规则表里明确要求的对照关系，全部已实现。"
        "中英文两种写法都认：核说 与 print 等价，核若 与 if 等价。",
        首行缩进=True,
    )

    标题(文档, "3.1  语句关键字", 2)
    表格(
        文档,
        ["核语言", "Python", "核语言", "Python"],
        [
            ["核若", "if", "核用 … 遍历 …", "for … in …"],
            ["又核若", "elif", "核循环若", "while"],
            ["核否则", "else", "核定义", "def"],
            ["核返回", "return", "核删", "del"],
            ["核否", "not", "核和", "and"],
            ["核或", "or", "核对 / 核错", "True / False"],
        ],
        列宽=[3.2, 4.6, 4.6, 4.6],
    )

    标题(文档, "3.2  内置函数", 2)
    表格(
        文档,
        ["核语言", "Python", "核语言", "Python", "核语言", "Python"],
        [
            ["核说", "print", "核整数", "int", "核长度", "len"],
            ["说核", "input", "核实数", "float", "核最小", "min"],
            ["核字符", "str", "核列表", "list", "核最大", "max"],
            ["核字典", "dict", "核集合", "set", "核排好", "sorted"],
            ["核绝对值", "abs", "核数列", "range", "核取舍", "round"],
        ],
        列宽=[2.9, 2.4, 2.9, 2.4, 2.9, 2.4],
    )

    标题(文档, "3.3  方法与关键字参数", 2)
    表格(
        文档,
        ["核语言", "Python", "说明"],
        [
            ["字符串.木亥（…）", ".split(…)", "按分隔符切开"],
            ["列表.核排序（）", ".sort()", "原地排序"],
            ["列表.核加入（…）", ".append(…)", "追加一个元素"],
            ["字符串.核找（…）", ".find(…) ", "返回位置，找不到为 -1"],
            ["字符串.核数（…）", ".count(…)", "统计出现次数"],
            ["字符串.核换（…）", ".replace(…)", "替换子串"],
            ["核说（…, 核尾=\"\"）", "print(…, end=\"\")", "不换行"],
            ["核说（…, 核隔=\"-\"）", "print(…, sep=\"-\")", "自定义分隔符"],
        ],
        列宽=[5.2, 6.0, 5.2],
    )
    正文(
        文档,
        "方法名只在点号之后生效，所以 核找 = 1 定义变量不会遇到问题；"
        "关键字参数只在「名字=」位置生效，所以 f(核尾) 这种位置参数也不会被误换。",
        首行缩进=True,
    )

    标题(文档, "3.4  字符串与注释", 2)
    表格(
        文档,
        ["写法", "含义"],
        [
            ["核\"总分{总分}，均分{平均:.2f}\"", "f 字符串；{x:.2f} 等格式说明原样保留"],
            ["核核 这是一行注释", "等价于 # 注释；# 也照样能用"],
            ["“ ”  ‘ ’  「 」  『 』", "代码区里都当普通引号处理"],
        ],
        列宽=[7.6, 8.8],
    )

    # —— 四、中英符号 ——
    标题(文档, "四、中英文符号视同", 1)
    正文(
        文档,
        "这是中文编程最实际的一个需求：输入法在中文状态时，敲出来的是全角标点。"
        "核语言在代码区自动把全角符号归一成半角，所以下面两行效果完全一样：",
        首行缩进=True,
    )
    代码块(
        文档,
        '核说（"你好，世界！"）     核核 全角括号、全角逗号\n'
        'print("你好，世界！")      核核 半角写法',
    )
    正文(
        文档,
        "归一的范围包括：，：；（）［］｛｝“”‘’＝＋－＊／％＜＞＆｜＾～＠＃＄＼＿、"
        "全角空格，以及全角数字与字母（１２３、ａｂｃ）。",
        首行缩进=True,
    )
    正文(
        文档,
        "关键的一点是：字符串内容和注释内容原样保留。"
        "所以「你好，世界！」里的中文逗号不会被改掉，显示出来的就是你写的字。",
        首行缩进=True,
    )

    # —— 五、未定义清单 ——
    标题(文档, "五、未定义清单：语言可以慢慢长大", 1)
    正文(
        文档,
        "这是核语言比较特别的一个设计。源码里如果出现了对照表没定义的英文写法，"
        "程序照常跑（原样交给 Python 执行），同时在当前目录记一笔到 未定义.txt：",
        首行缩进=True,
    )
    代码块(
        文档,
        "# 核语言 未定义清单\n"
        "# 格式：写法 | 类别 | 次数 | 首次位置 | 最近位置（文件内用制表符分隔）\n"
        "\n"
        "sum         内置函数   2   例子/05_未定义演示.xht:9:19    例子/05_未定义演示.xht:12:5\n"
        "type        内置函数   1   例子/05_未定义演示.xht:15:14   例子/05_未定义演示.xht:15:14\n"
        "capitalize  方法       1   例子/05_未定义演示.xht:12:12   例子/05_未定义演示.xht:12:12\n"
        "file        参数名     1   例子/05_未定义演示.xht:18:14   例子/05_未定义演示.xht:18:14",
    )
    要点(文档, "同一个写法只记一条，次数累加，位置记首次与最近。", "跨运行累积。")
    要点(文档, "位置写成相对清单文件的路径，点开就能定位到具体行列。", "可定位。")
    要点(文档, "赋值左边的名字、核定义 定义的函数名不算未定义。", "不误报。")

    正文(文档, "看到清单后，补进对照表就变成中文了，例如在 核.py 的函数表里加一行：", 段前=6, 段后=2)
    代码块(文档, '"核求和": "sum",')
    正文(文档, "再运行，核求和（…） 就能用了，清单里这一条也不再出现。", 首行缩进=True)

    # —— 六、界面 ——
    标题(文档, "六、图形界面：核工坊", 1)
    正文(
        文档,
        "核工坊是一个 PyCharm 风格的集成开发环境，用 tkinter 写成，"
        "不依赖任何第三方界面库。界面区域自上而下依次是："
        "集成式标题栏（应用标、项目名、搜索框、汉堡菜单）、"
        "主工具条（运行、停止、保存、打开，右侧显示面包屑）、"
        "左侧竖排工具条（项目、对照表、运行、停止、齿轮）、"
        "项目树、标签页编辑器、右侧语法对照表、底部运行窗口与状态栏。",
        首行缩进=True,
    )
    正文(
        文档,
        "编辑器提供语法高亮（关键字、内置函数、方法、字符串、数字、注释）、"
        "行号与当前行、缩进参考线、自动缩进、括号补全式的回车缩进、"
        "查找替换、转到行、注释切换，以及深色与浅色两套主题。",
        首行缩进=True,
    )

    插图(
        文档,
        os.path.join(这里, "截图_核工坊.png"),
        "核工坊主界面（深色主题）：左侧竖排工具条、项目树、标签页编辑器、语法对照表、底部运行窗口",
        宽=Cm(16.0),
        分页=True,
    )
    插图(
        文档,
        os.path.join(这里, "截图_核工坊_浅色.png"),
        "核工坊主界面（浅色主题）：同一套布局，仅切换配色方案",
        宽=Cm(16.0),
        分页=True,
    )
    插图(
        文档,
        os.path.join(这里, "截图_欢迎页.png"),
        "欢迎页：没有打开文件时的起始界面",
        宽=Cm(13.0),
        分页=True,
    )

    标题(文档, "6.1  常用快捷键", 2)
    表格(
        文档,
        ["快捷键", "作用", "快捷键", "作用"],
        [
            ["F5", "运行", "Ctrl+S", "保存"],
            ["Shift+F5", "停止", "Ctrl+N", "新建"],
            ["F9", "检查语法", "Ctrl+O", "打开文件"],
            ["Ctrl+F", "查找替换", "Ctrl+G", "转到行"],
            ["Ctrl+/", "注释切换", "Ctrl+滚轮", "缩放字号"],
        ],
        列宽=[3.4, 4.2, 3.4, 4.2],
    )

    # —— 七、命令行 ——
    标题(文档, "七、命令行与自测", 1)
    表格(
        文档,
        ["命令", "作用"],
        [
            ["核 文件.xht", "运行程序"],
            ["核 检查 文件.xht", "只做语法检查，不运行"],
            ["核 转译 文件.xht", "打印转译后的 Python 代码"],
            ["核 报告", "查看未定义清单"],
            ["核 工坊", "打开图形界面"],
            ["核", "进入交互模式，核退出 结束"],
        ],
        列宽=[6.4, 9.8],
    )

    正文(
        文档,
        "项目自带两套自测，都是标准库 unittest 或纯断言，不依赖第三方包：",
        段前=6,
    )
    表格(
        文档,
        ["自测", "项目数", "覆盖内容"],
        [
            ["测试/自测.py", "23", "转译规则、运行结果、错误行号、未定义清单"],
            ["测试/界面自测.py", "39", "外壳布局、编辑、运行、停止、查找替换、缩进线、主题"],
        ],
        列宽=[4.6, 2.2, 9.6],
    )
    代码块(
        文档,
        "python 测试/自测.py\npython 测试/界面自测.py",
    )

    # —— 八、打包 ——
    标题(文档, "八、打包成 exe", 1)
    正文(
        文档,
        "用 PyInstaller 可以把核工坊打成单个 Windows 可执行文件。"
        "打包版内置内核：运行用户程序时调用 exe 自身（参数 --内核），"
        "所以目标机器不需要安装 Python。",
        首行缩进=True,
    )
    代码块(
        文档,
        "pip install -i https://pypi.tuna.tsinghua.edu.cn/simple pyinstaller\n"
        "python 测试/打包.py           核核 单文件，约 29 MB\n"
        "python 测试/打包.py --目录     核核 文件夹形式，启动更快",
    )
    正文(
        文档,
        "实测环境：Python 3.12、PyInstaller 6.22，产物 28.9 MB；"
        "在 PATH 中不含任何 Python 的情况下仍能正常打开界面并运行 .xht 程序。",
        首行缩进=True,
    )

    # —— 九、目录结构 ——
    标题(文档, "九、目录结构", 1)
    代码块(
        文档,
        "核.py              内核：转译器 + 命令行 + 交互模式\n"
        "核工坊.py          图形界面（PyCharm 风格）\n"
        "设置窗口.py        设置弹窗（Ctrl+,）\n"
        "拖放.py            文件拖入（Windows 原生）\n"
        "圆角.py            窗口与控件圆角\n"
        "启动器.py          打包入口，同时充当内置内核\n"
        "核.cmd / 核工坊.cmd  双击启动器\n"
        "素材/              图标（PNG 与多尺寸 ICO）\n"
        "例子/              5 个示例程序\n"
        "测试/              自测、截图、打包、归档、发布脚本\n"
        "版本/              各版本源码快照\n"
        "说明.md            详细说明书\n"
        "版本记录.md        版本历史与发布流程\n"
        "未定义.txt         未定义写法清单（运行后生成并累积）",
        说明="项目根目录",
    )

    # —— 十、限制 ——
    标题(文档, "十、已知限制与后续方向", 1)
    正文(文档, "第一版有意控制范围，以下几处是有意为之的取舍：", 首行缩进=True)
    要点(文档, "转译器是逐字符扫描，不做完整语法树分析，"
                "极少数写法（例如把关键字拼进字符串前缀位置）可能与直觉不同。", "无 AST 分析。")
    要点(文档, "只识别英文写法；中文里没定义的新词按普通变量名处理。", "清单只收英文。")
    要点(文档, "没有断点调试、代码补全、工程级重构。", "界面功能精简。")
    要点(文档, "tkinter 的原生菜单条无法与窗口标题栏合并，"
                "所以菜单仍独占一行，其余部分与 PyCharm 新 UI 一致。", "标题栏。")
    末条 = 要点(文档, "补全未定义清单里的常用写法、增加 AST 级语法检查、用 Nuitka 编译瘦身。",
              "后续方向。")
    末条.paragraph_format.space_after = Pt(14)
    尾签 = 末条.add_run()
    尾签.add_break()
    尾签 = 末条.add_run("—— 核语言 0.0.1 · 用中文写程序 ——")
    设置字体(尾签, 正文体, 9, False, 灰字)



    return 文档



if __name__ == "__main__":
    输出 = os.path.join(这里, "核语言介绍.docx")
    文档 = 建文档()
    文档.save(输出)
    print("已生成：%s（%.1f KB）" % (输出, os.path.getsize(输出) / 1024.0))
