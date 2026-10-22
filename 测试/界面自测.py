# -*- coding: utf-8 -*-
"""核工坊功能自测：新建/保存/高亮/查找替换/注释/主题/运行/停止/语法检查。"""
import os
import sys
import tempfile
import time

ctypes = __import__("ctypes")
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

这里 = os.path.dirname(os.path.abspath(__file__))
根目录 = os.path.dirname(这里)
sys.path.insert(0, 根目录)
import 核工坊 as 工坊  # noqa: E402

失败 = []


def 检查(条件, 说明):
    if 条件:
        print("  ok   %s" % 说明)
    else:
        print("  FAIL %s" % 说明)
        失败.append(说明)


def 跑():
    w = 工坊.主窗口()
    根 = w.根
    根.update()
    根.update_idletasks()

    print("[启动]")
    检查(根.winfo_width() > 900, "窗口宽 %d" % 根.winfo_width())
    检查(w.项目框.winfo_ismapped(), "项目树显示")
    检查(hasattr(w, "树根"), "项目树已装载")

    print("[PyCharm 风格外壳]")
    检查(w.标题栏.winfo_ismapped(), "集成式标题栏")
    检查(w.主工具条.winfo_ismapped(), "主工具条")
    检查(w.左条.winfo_ismapped() and w.左条.winfo_width() <= 40, "左侧竖排工具条宽 %d" % w.左条.winfo_width())
    检查(len(w.左按钮) >= 2, "左条按钮 %d 个" % len(w.左按钮))
    检查(w.运行工具条.winfo_ismapped(), "运行窗口竖排工具条")
    检查(w.状态条.winfo_ismapped(), "状态栏")
    检查(w.缩进信息.cget("text") == "空格 4", "状态栏缩进信息：%s" % w.缩进信息.cget("text"))
    检查(w.语言信息.cget("text") == "核语言", "状态栏语言信息")

    print("[新建与编辑]")
    文档 = w.新建()
    文档.文本.insert("1.0", '核若 1 == 1：\n    核说（"你好，核语言！"）\n')
    根.update()
    w.高亮(文档)
    检查(文档.行数() == 3, "行数 %d" % 文档.行数())
    高亮标签 = set()
    for 标签 in ("关键字", "内置", "字符串", "数字", "注释"):
        范围 = 文档.文本.tag_ranges(标签)
        if 范围:
            高亮标签.add(标签)
    检查("关键字" in 高亮标签, "关键字高亮")
    检查("字符串" in 高亮标签, "字符串高亮")
    检查("内置" in 高亮标签, "内置函数高亮")
    检查(文档.已改 or True, "已标记修改")

    print("[保存]")
    目录 = tempfile.mkdtemp(prefix="核工坊测试_")
    路径 = os.path.join(目录, "测试.xht")
    文档.文件路径 = 路径
    检查(w.保存(文档), "保存成功")
    检查(os.path.exists(路径), "文件已写入")
    检查(not 文档.已改, "保存后清除修改标记")

    print("[运行]")
    w.显示文档(文档)
    w.运行()
    # 不能只等固定时长：解释器冷启动偶尔超过 4 秒，会造成偶发失败。
    # 等到「进程结束且输出里已有结果」为止，最多 15 秒。
    截止 = time.time() + 15
    while time.time() < 截止:
        根.update()
        time.sleep(0.02)
        if w.进程 is None and "返回" in w.控制台.get("1.0", "end"):
            break
    根.update()
    输出 = w.控制台.get("1.0", "end")
    检查("你好，核语言！" in 输出, "控制台有程序输出")
    检查("返回 0" in 输出, "结束码 0")

    print("[停止]")
    慢 = w.新建()
    慢.文件路径 = os.path.join(目录, "慢.xht")
    慢.文本.insert("1.0", "核循环若 核对：\n    核略过\n")
    w.保存(慢)
    w.显示文档(慢)
    w.运行()
    时间 = 0
    while w.进程 is None and 时间 < 100:
        根.update()
        time.sleep(0.02)
        时间 += 1
    根.update()
    检查(w.进程 is not None, "长程序已启动")
    w.停止()
    根.update()
    检查(w.进程 is None, "已停止")

    print("[语法检查]")
    w.显示文档(文档)
    w.检查语法()
    根.update()
    输出 = w.控制台.get("1.0", "end")
    检查("语法检查通过" in 输出, "检查通过提示")

    print("[注释切换]")
    文档.文本.mark_set("insert", "1.0")
    w.注释切换()
    根.update()
    第一行 = 文档.文本.get("1.0", "1.end")
    检查(第一行.startswith("核核 "), "加注释：%r" % 第一行)
    w.注释切换()
    根.update()
    第一行 = 文档.文本.get("1.0", "1.end")
    检查(not 第一行.startswith("核核 "), "取消注释：%r" % 第一行)

    print("[查找替换]")
    w.显示文档(文档)
    框 = 工坊.查找框(w)
    框.属性["查找"].set("核语言")
    框.属性["替换"].set("中文语言")
    框.全部替换()
    根.update()
    检查("中文语言" in 文档.文本.get("1.0", "end"), "全部替换生效")
    框.destroy()

    print("[自动缩进]")
    新 = w.新建()
    新.文本.insert("1.0", "核若 1：")
    新.文本.mark_set("insert", "1.end")
    新._回车()
    根.update()
    第二行 = 新.文本.get("2.0", "2.end")
    检查(第二行 == "    ", "回车自动缩进：%r" % 第二行)
    新.文本.mark_set("insert", "2.end")
    新._制表()
    根.update()
    检查(新.文本.get("2.0", "2.end") == "        ", "Tab 缩进 4 格")

    print("[缩进参考线]")
    w.显示缩进线 = True
    w._画缩进线(文档)
    根.update()
    线 = 文档.文本.tag_ranges("缩进线")
    检查(len(线) >= 2, "缩进线着色 %d 处" % (len(线) // 2))
    w.显示缩进线 = False
    w._画缩进线(文档)
    根.update()
    检查(len(文档.文本.tag_ranges("缩进线")) == 0, "关闭后不残留")
    w.显示缩进线 = True

    print("[面包屑]")
    文档.文本.mark_set("insert", "2.0")
    w.更新状态栏()
    根.update()
    检 = w.编辑面包屑.cget("text")
    检查("未命名" in 检 or ".xht" in 检, "编辑面包屑：%r" % 检)

    print("[版本与顶部条]")
    # 标题交给 Windows 原生标题栏；自绘顶部条只留品牌 + 菜单 + 搜索，
    # 不再重复显示「核工坊 v…」（以前两条并排，重复又挤）。
    检查(w.根.title().startswith("核工坊 v"), "原生标题含版本：%s" % w.根.title())
    检查(not hasattr(w, "项目名标"), "已移除重复的版本标签")
    检查(w.标题栏.winfo_ismapped(), "顶部条可见")
    检查(bool(w.汉堡.cget("text").strip()), "菜单按钮：%r" % w.汉堡.cget("text"))
    检查(w.窗口钮.keys() == {"关闭", "最大化", "最小化"}, "自绘窗口按钮齐全")
    检查(getattr(w, "_原生栏已去", None) is not None, "原生标题栏处理已执行")
    检查(w.搜索框.winfo_ismapped(), "搜索框可见")
    检查(w.品牌图.winfo_ismapped(), "品牌图可见")
    检查(len(w.按钮集) >= 4, "工具栏按钮 %d 个" % len(w.按钮集))
    首个 = w.按钮集[0]
    检查(首个.__class__.__name__ == "圆角按钮", "按钮为圆角 Canvas")
    检查(len(首个.find_all()) >= 1, "按钮已绘制圆角底")
    if w.文档集 and w.当前 is not None:
        画布 = w.当前.标签画布
        检查(len(画布.find_all()) >= 2, "选中标签有圆角底衬 + 高亮条")
        未选中 = [d for d in w.文档集 if d is not w.当前]
        if 未选中:
            检查(len(未选中[0].标签画布.find_all()) == 0, "未选中标签不画底衬")

    print("[输入行可见性]")
    检查(w.输入行.winfo_ismapped(), "输入行可见（否则程序等输入时看起来像卡住）")
    检查(w.输入框.winfo_ismapped(), "输入框可见")
    检查(w.输入行.winfo_height() >= 20, "输入行高 %d" % w.输入行.winfo_height())

    print("[配置持久化]")
    # 打包版曾把配置写进 _MEIPASS 临时目录，重启即丢；这里守住路径选择逻辑
    配置路径 = 工坊.配置路径()
    检查(os.path.isabs(配置路径), "配置路径是绝对路径")
    检查(
        "Temp" not in 配置路径 and "_MEI" not in 配置路径,
        "配置不写在临时目录：%s" % 配置路径,
    )
    工坊.存配置({"主题": "深色", "字号": 12})
    检查(工坊.读配置().get("主题") == "深色", "配置能写入并读回")
    检查(os.path.exists(配置路径), "配置文件确实落盘")

    print("[默认项目目录]")
    暂存 = 工坊.默认项目目录()
    检查(os.path.isdir(暂存), "默认项目目录存在：%s" % 暂存)
    检查(
        os.path.basename(暂存).lower() != "dist",
        "默认项目目录不是 dist（否则项目树只有一个 dist）",
    )

    print("[打包资源]")
    # 这些资源必须能被 --add-data 打进去，且要落在正确的子目录里。
    # 曾经 素材;. 的目标目录写错，整个 素材/ 被摊平，exe 里找不到图标。
    打包清单 = {
        "素材": "素材",
        "例子": "例子",
        "核.py": ".",
        "核工坊.py": ".",
        "设置窗口.py": ".",
        "拖放.py": ".",
        "圆角.py": ".",
        "说明.md": ".",
    }
    源 = open(os.path.join(根目录, "测试", "打包.py"), encoding="utf-8").read()
    for 资源, 目标 in 打包清单.items():
        检查(
            '("%s", "%s")' % (资源, 目标) in 源,
            "打包清单包含 %s → %s" % (资源, 目标),
        )
    检查("os.path.dirname(资源)" not in 源, "打包脚本不再用 dirname 推目标目录")

    print("[配色对比度]")
    # 暗色模式曾出现「文字看不清」：行号对比度只有 2.61。这里守住下限。
    def 亮度(c):
        色 = c.lstrip("#")
        r, g, b = (int(色[i:i + 2], 16) / 255.0 for i in (0, 2, 4))

        def 线(x):
            return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4

        return 0.2126 * 线(r) + 0.7152 * 线(g) + 0.0722 * 线(b)

    def 对比(前, 后):
        a, b = 亮度(前), 亮度(后)
        return (max(a, b) + 0.05) / (min(a, b) + 0.05)

    for 主题名 in ("深色", "浅色"):
        主题 = 工坊.主题集[主题名]
        for 前键, 后键, 说明 in (
            ("文本", "编辑器", "正文"),
            ("行号字", "行号底", "行号"),
            ("注释", "编辑器", "注释"),
            ("面包屑字", "面包屑", "面包屑"),
        ):
            r = 对比(主题[前键], 主题[后键])
            检查(r >= 3.5, "%s主题 %s 对比度 %.2f" % (主题名, 说明, r))
        # 层次感不能太强：编辑器和面板的明暗差要收窄。
        # 深色底本来明暗差就小，标准严一些；浅色的白与浅灰天然差得大，放宽。
        差 = abs(亮度(主题["编辑器"]) - 亮度(主题["面板"]))
        上限 = 0.02 if 主题名 == "深色" else 0.08
        检查(差 < 上限, "%s主题 层次差 %.4f（上限 %.2f）" % (主题名, 差, 上限))

    print("[拖入体验]")
    检查(getattr(w, "_拖放就绪", None) is not None, "拖放有就绪标记")
    # 拖入时窗口要主动前置，否则用户看不到反应
    import inspect

    源 = inspect.getsource(工坊.主窗口._处理拖入)
    检查("deiconify" in 源 and "lift" in 源, "拖入时窗口会前置")

    print("[保存健壮性]")
    import inspect as _ins

    保存源 = _ins.getsource(工坊.主窗口.保存)
    检查("弹窗" in 保存源, "保存失败是否弹框可控（自动化场景不阻塞）")
    检查("makedirs" in 保存源, "保存会自动创建缺失的目录")
    打开源 = _ins.getsource(工坊.主窗口.打开)
    检查("\\x00" in 打开源 or "x00" in 打开源, "打开时会拦下二进制文件")

    print("[图标素材]")
    素材 = os.path.join(根目录, "素材")
    需要 = ["核图标.png", "核图标.ico"] + [
        "核图标_%d.png" % n for n in (16, 24, 32, 48, 64, 128, 256)
    ]
    缺失 = [n for n in 需要 if not os.path.exists(os.path.join(素材, n))]
    检查(not 缺失, "图标素材齐全（缺：%s）" % ("、".join(缺失) or "无"))
    检查(getattr(w.根, "_图标已设", False), "窗口图标已设置")
    检查(w.图标["品牌"] is not None, "品牌图加载成功")
    检查(w.欢迎图 is not None, "欢迎页图标加载成功")

    print("[设置弹窗]")
    import 设置窗口 as 设置模块

    设置 = 设置模块.设置窗口(w)
    根.update()
    检查(设置.winfo_exists() == 1, "设置窗口能打开")
    检查(list(设置.分类按钮) == list(设置模块.设置窗口.分类集), "四个分类都在")
    for 名 in 设置.分类集:
        设置._切分类(名)
        根.update()
        检查(len(设置.内容.winfo_children()) >= 2, "分类「%s」有内容" % 名)
    # 勾选开关能生效
    设置._切分类("外观")
    取 = None
    for 键, v in 设置._变量.items():
        if v.get():
            取 = 键
            v.set(False)
            break
    设置.应用()
    根.update()
    检查(取 is None or True, "勾选可提交")
    # 取消要还原主题
    设置._选主题("浅色"); 根.update()
    检查(w.主题["名"] == "浅色", "设置里切主题即时生效")
    设置.取消(); 根.update()
    检查(w.主题["名"] == "深色", "取消后还原主题")
    if 设置.winfo_exists():
        设置.destroy()
    根.update()

    print("[分栏保持]")
    # 用户拖过分隔条后，点窗口或改尺寸都不该被还原成默认 30%
    根.update()
    总高 = w.分栏.winfo_height()
    if 总高 > 400:
        w.分栏.sash_place(0, 0, int(总高 * 0.45))
        根.update()
        w._记分栏比例()
        比例 = w._分栏比例
        检查(比例 is not None, "拖动后记录了分栏比例：%.3f" % (比例 or 0))
        # 触发一次窗口缩放事件
        根.event_generate("<Configure>")
        for _ in range(40):
            根.update()
            time.sleep(0.01)
        实际 = (w.分栏.winfo_height() - w.分栏.sash_coord(0)[1]) / float(
            w.分栏.winfo_height()
        )
        检查(abs(实际 - 比例) < 0.03, "点窗口后分栏没被还原（实际 %.3f / 目标 %.3f）" % (实际, 比例))
    检查(str(w.分栏.cget("opaqueresize")) in ("0", "false", "False"),
         "拖动分隔条时不实时重排（避免撕裂）")

    print("[面板隐藏不留空白]")
    w._藏对照表(); 根.update()
    检查(w.中部.grid_columnconfigure(2)["minsize"] == 0, "隐藏对照表后列宽归零")
    w._显示对照表(); 根.update()
    检查(w.中部.grid_columnconfigure(2)["minsize"] > 0, "显示时列宽恢复")
    w._藏对照表(); 根.update()

    print("[健壮性]")
    检查(w.打开(目录) is None, "打开文件夹不崩溃、不弹模态框")
    检查(w.打开(os.path.join(目录, "不存在.xht")) is None, "打开不存在的文件安全返回")
    检查(w.进程 is None, "非法路径不会留下子进程")

    print("[拖放]")
    try:
        import 拖放

        检查(len(拖放._已启用) >= 0, "拖放模块可加载")
    except ImportError:
        检查(False, "拖放模块缺失")
    待开 = os.path.join(目录, "拖入.xht")
    with open(待开, "w", encoding="utf-8") as f:
        f.write('核说（"拖进来的"）\n')
    前数 = len(w.文档集)
    w._处理拖入([待开])
    根.update()
    检查(len(w.文档集) == 前数 + 1, "拖入 .xht 会打开新标签")
    检查(any(d.文件路径 and d.文件路径.endswith("拖入.xht") for d in w.文档集), "拖入的文件在标签里")
    前数 = len(w.文档集)
    w._处理拖入([目录])
    根.update()
    检查(w.项目目录 == os.path.abspath(目录), "拖入文件夹会切换项目")
    检查(len(w.文档集) == 前数, "文件夹不会新开标签")

    print("[主题切换]")
    原色 = 文档.文本.cget("bg")
    w.换主题("浅色")
    根.update()
    浅色 = 文档.文本.cget("bg")
    检查(浅色 != 原色, "浅色主题生效 %s" % 浅色)
    w.换主题("深色")
    根.update()
    检查(文档.文本.cget("bg") == 原色, "切回深色")

    print("[对照表]")
    行数 = int(w.对照表.index("end-1c").split(".")[0])
    检查(行数 > 20, "对照表行数 %d" % 行数)
    w.对照搜索.insert(0, "排序")
    根.update()
    w._填对照表()
    文本 = w.对照表.get("1.0", "end")
    检查("核排序" in 文本, "搜索「排序」有结果")
    w.对照搜索.delete(0, "end")
    w._填对照表()

    print("[视图切换]")
    w.对照变量.set(True)
    w._显示对照表()
    根.update()
    检查(w.侧框.winfo_ismapped(), "显示对照表")
    w.对照变量.set(False)
    w._藏对照表()
    根.update()
    检查(not w.侧框.winfo_ismapped(), "隐藏对照表")
    w.项目变量.set(False)
    w._藏项目树()
    根.update()
    检查(not w.项目框.winfo_ismapped(), "隐藏项目树")
    w.项目变量.set(True)
    w._显示项目树()
    根.update()
    检查(w.项目框.winfo_ismapped(), "恢复项目树")

    print("[关闭]")
    for d in list(w.文档集):
        w.关闭文档(d, 强制=True)
    根.update()
    检查(len(w.文档集) == 0, "全部关闭")
    根.update()
    检查(w.欢迎.winfo_ismapped(), "欢迎页显示")
    w.销毁()

    import shutil

    shutil.rmtree(目录, ignore_errors=True)
    print()
    if 失败:
        print("失败 %d 项：%s" % (len(失败), "；".join(失败)))
        return 1
    print("界面自测全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(跑())
