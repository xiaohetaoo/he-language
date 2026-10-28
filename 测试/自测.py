# -*- coding: utf-8 -*-
"""核语言自测：python 测试/自测.py

用自己的转译器跑一批用例，检查输出、错误提示和未定义清单。
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

这里 = os.path.dirname(os.path.abspath(__file__))
根目录 = os.path.dirname(这里)
if 根目录 not in sys.path:
    sys.path.insert(0, 根目录)

import 核 as 内核  # noqa: E402

解释器 = sys.executable
内核脚本 = os.path.join(根目录, "核.py")


def 转译(源码, 报告=None):
    return 内核.转译(源码, "<测试>", 报告)


class 转译测试(unittest.TestCase):
    def 断言转译(self, 源, 期望):
        self.assertEqual(转译(源).strip(), 期望.strip(), msg="源码：%r" % 源)

    def test_关键字(self):
        self.断言转译("核若 1：\n    核说（1）", 'if 1:\n    print(1)')
        self.断言转译("核否则：\n    核略过", "else:\n    pass")
        self.断言转译("又核若 核错：\n    核略过", "elif False:\n    pass")
        self.断言转译("核用 i 遍历 核数列（3）：\n    核说（i）", "for i in range(3):\n    print(i)")
        self.断言转译("核循环若 核对：\n    核断开", "while True:\n    break")
        self.断言转译("核定义 f（x）：\n    核返回 x", "def f(x):\n    return x")
        self.断言转译("核删 a", "del a")
        self.断言转译("核若 核否 核错 核和 核对 核或 核错：\n    核略过", "if not False and True or False:\n    pass")

    def test_内置函数(self):
        self.断言转译("核说（核整数（“3”））", 'print(int("3"))')
        self.断言转译("核说（核实数（“1.5”））", 'print(float("1.5"))')
        self.断言转译("核说（核字符（1））", "print(str(1))")
        self.断言转译("核说（核长度（核列表（）））", "print(len(list()))")
        self.断言转译("核说（核最小（1, 2）, 核最大（1, 2））", "print(min(1, 2), max(1, 2))")
        self.断言转译("核说（核绝对值（-1）, 核取舍（1.5））", "print(abs(-1), round(1.5))")
        self.断言转译("核说（核排好（[3, 1]））", "print(sorted([3, 1]))")
        self.断言转译("核说（核字典（）, 核集合（））", "print(dict(), set())")

    def test_方法(self):
        self.断言转译("a.木亥（“,”）", 'a.split(",")')
        self.断言转译("a.核排序（）", "a.sort()")
        self.断言转译("a.核加入（1）", "a.append(1)")
        self.断言转译("a.核找（“x”）", 'a.find("x")')
        self.断言转译("a.核数（“x”）", 'a.count("x")')
        self.断言转译("a.核换（“x”, “y”）", 'a.replace("x", "y")')
        # 方法名只在点之后生效，普通位置不该被换掉
        self.断言转译("核找 = 1\n核说（核找）", "核找 = 1\nprint(核找)")
        # 点后有空格的写法也认
        self.断言转译("a . 木亥 （）", "a . split ()")

    def test_关键字参数(self):
        self.断言转译('核说（1, 核尾=“”）', "print(1, end=\"\")")
        self.断言转译('核说（1, 2, 核隔=“-”）', 'print(1, 2, sep="-")')
        # 位置参数里的名字不能被当成关键字参数
        self.断言转译("f(核尾)", "f(核尾)")

    def test_全角标点(self):
        self.断言转译("核说（“你好，世界！”）", 'print("你好，世界！")')
        self.断言转译("核说（「引号也认」）", 'print("引号也认")')
        self.断言转译("核若 （1 ＋ 2）＞2：\n    核说（“大”）", 'if (1 + 2)>2:\n    print("大")')
        # 字符串内容里的全角标点必须原样保留
        译 = 转译('核说（"a，b（c）"）')
        self.assertIn("a，b（c）", 译)
        # 注释内容同样保留
        self.assertIn("# 中文：注释（保留）", 转译("核核 中文：注释（保留）"))

    def test_注释(self):
        self.断言转译("核核 说明", "# 说明")
        self.断言转译("核说（1）核核 尾注", "print(1)# 尾注")
        self.断言转译("# Python 式注释也行", "# Python 式注释也行")

    def test_f字符串(self):
        self.断言转译('x=1\n核说（核“值{x}”）', 'x=1\nprint(f"值{x}")')
        self.断言转译('核说（核“{x:.2f}”）', 'print(f"{x:.2f}")')
        self.断言转译('核说（核“{核长度(x)}”）', 'print(f"{len(x)}")')
        self.断言转译('核说（f“{x}”）', 'print(f"{x}")')
        self.断言转译('核说（核“{{原样}}”）', 'print(f"{{原样}}")')

    def test_英文兼容(self):
        self.断言转译('print("a")\nif 1:\n    pass', 'print("a")\nif 1:\n    pass')
        self.断言转译("[x for x in range(3)]", "[x for x in range(3)]")

    def test_数字(self):
        self.断言转译("核说（-1.5, 1e3, 0x1F, 1_000）", "print(-1.5, 1e3, 0x1F, 1_000)")
        self.断言转译("a.b", "a.b")
        self.断言转译("核说（1..2）", "print(1..2)")

    def test_未定义记录(self):
        报告 = 内核.未定义报告(None)
        转译(
            "核说（ascii（1））\n核说（bytearray（1））\n“x”.casefold（）\n核说（1, 核尾=核对）",
            报告,
        )
        类别 = set(报告.条目)
        self.assertIn(("ascii", "内置函数"), 类别)
        self.assertIn(("bytearray", "内置函数"), 类别)
        self.assertIn(("casefold", "方法"), 类别)
        # 已定义的参数（核尾→end）不该被记成未定义
        self.assertNotIn(("核尾", "参数名"), 类别)
        self.assertNotIn(("end", "参数名"), 类别)

    def test_已定义英文不记未定义(self):
        报告 = 内核.未定义报告(None)
        转译(
            "核说（len（“abc”））\n核说（sorted（[2, 1]））\n“x”.upper（）\n核说（1, end=“”）",
            报告,
        )
        self.assertEqual(报告.条目, {}, msg="中英都认的写法不该进未定义清单")

    def test_BOM(self):
        # 用 chr(0xFEFF) 构造 BOM，避免源码里直接出现不可见字符
        bom = chr(0xFEFF)
        self.断言转译(bom + "核说（1）", "print(1)")
        self.assertEqual(转译(bom + "核说（1）" + chr(10)).strip(), "print(1)")

    def test_未定义不误报(self):
        # 赋值语句左边的名字是用户自己定义的，不该记进未定义清单
        报告 = 内核.未定义报告(None)
        转译("len = 3\n核说（len）\n核说（ascii）", 报告)
        self.assertEqual(list(报告.条目), [("ascii", "内置函数")])

    # —— 以下为 0.0.13 的修复补测 ——

    def test_嵌套f字符串(self):
        """字段里再放一个中文 f-string 也要转对（PEP 701）。"""
        self.断言转译(
            '核说（核“外层{核“内层”}结束”）',
            'print(f"外层{f"内层"}结束")',
        )
        # 同样结构的英文写法则本来就是合法源码，原样保留
        译 = 转译('核说（f“外层{f“内层”}结束”）')
        self.assertEqual(译.strip(), 'print(f"外层{f"内层"}结束")')
        # 产物必须真的能编译（这才是当初真正失败的地方：
        # 内层的「核"」没被转成 f"，报的是晦涩的 f-string: expecting '='）
        compile(译, "<测试>", "exec")
        # 字段里带格式说明、带下标的也要照旧
        self.断言转译(
            '核说（核“{核长度(a[0]):>3}”）',
            'print(f"{len(a[0]):>3}")',
        )

    def test_未闭合字符串不再被悄悄补引号(self):
        """文件末尾写了一半的字符串，不能替用户补上收尾引号。"""
        译 = 转译('x = "abc')
        self.assertEqual(译.strip(), 'x = "abc', msg="不该自动补引号：%r" % 译)
        # 交给 Python 报错，而且报错信息要是中文提示
        import io

        流 = io.StringIO()
        代码, _ = 内核.编译源码('x = "abc', "<测试>", None, 流)
        self.assertIsNone(代码)
        提示 = 流.getvalue()
        self.assertIn("语法错误", 提示)
        self.assertIn("引号没有配上对", 提示, msg="缺少中文提示：%r" % 提示)
        # 正常闭合的字符串不受影响
        self.assertEqual(转译('x = "abc"').strip(), 'x = "abc"')

    def test_字符串里的全角右引号不收尾(self):
        """ASCII 引号只认 ASCII 引号收尾。

        「」『』 在规范化的「收尾集」里只管中文引号开头的情形；
        把 」 也算成 " 的收尾符，会让
        核说（“成绩里没有「数学」这一项”）这种东西直接编译不过。
        """
        self.断言转译(
            '核说（"成绩里没有「数学」这一项"）',
            'print("成绩里没有「数学」这一项")',
        )
        self.断言转译('核说（「含"引号"的串」）', 'print("含\\"引号\\"的串")')

    def test_中文引号左右各自配对(self):
        """「 只由 」收尾，“ 只由 ”收尾 —— 中文里套一层是常见写法。

        以前 「」『』“” 六个字符共用一个收尾集，于是
        核说（“成绩里没有「数学」这一项”） 里的 」 被当成外层 “ 的收尾符，
        字符串从中间断开、产物编译不过（HEAD 上实测就是这个结果）。
        """
        self.断言转译(
            "核说（“成绩里没有「数学」这一项”）",
            'print("成绩里没有「数学」这一项")',
        )
        self.断言转译("核说（“外层『内层』结束”）", 'print("外层『内层』结束")')
        self.断言转译("核说（『只有书名号』）", 'print("只有书名号")')
        self.断言转译("核说（‘单引号也认’）", "print('单引号也认')")
        # f-string 的普通文本里也能放「」
        self.断言转译(
            '核说（核“叫声是「{x}」”）',
            'print(f"叫声是「{x}」")',
        )

    def test_扫描行(self):
        """字符串区间 / 注释起点 / 跨行三引号，一次扫完。"""
        区间, 注释起, 未闭合 = 内核.扫描行('核说("核若")  核核 注释')
        self.assertEqual(区间, [(3, 7)])
        self.assertEqual(注释起, 10)
        self.assertIsNone(未闭合)
        # 注释里的引号不是字符串
        区间, 注释起, _ = 内核.扫描行('核核 说明 "这不是字符串"')
        self.assertEqual(区间, [])
        self.assertEqual(注释起, 0)
        # 字符串里的「核核」不是注释
        区间, 注释起, _ = 内核.扫描行("核说('核核 在串里')")
        self.assertEqual(区间, [(3, 11)])
        self.assertEqual(注释起, -1)
        # 三引号没在本行收尾
        区间, 注释起, 未闭合 = 内核.扫描行('核说("""第一行')
        self.assertEqual(区间, [(3, 9)])
        self.assertEqual(未闭合, '"""')
        # 续行：整行都在字符串里
        区间, 注释起, 未闭合 = 内核.扫描行("第二行 核若", '"""')
        self.assertEqual(区间, [(0, 6)])
        self.assertEqual(未闭合, '"""')
        # 续行里遇到收尾
        区间, _, 未闭合 = 内核.扫描行('结束""" 核说(1)', '"""')
        self.assertEqual(区间, [(0, 5)])
        self.assertIsNone(未闭合)

    def test_报告共享不被互相冲掉(self):
        """运行 与 检查语法 各拿一个报告实例时，后写的会冲掉先写的。

        共享同一个实例（核.取报告）之后，两边都只是往同一份字典里加条目。
        """
        目录 = tempfile.mkdtemp(prefix="核语言报告_")
        路径 = os.path.join(目录, "未定义.txt")
        甲 = 内核.取报告(路径)
        甲.记录("ascii", "内置函数", "a.xht", 1, 1)
        甲.保存()
        乙 = 内核.取报告(路径)
        self.assertIs(甲, 乙, "同一路径必须拿到同一个实例")
        乙.记录("bytearray", "内置函数", "b.xht", 2, 1)
        乙.保存()
        丙 = 内核.未定义报告(路径)
        self.assertIn(("ascii", "内置函数"), 丙.条目)
        self.assertIn(("bytearray", "内置函数"), 丙.条目)
        # 空路径不缓存，也不该抛
        self.assertIsNotNone(内核.取报告(None))
        shutil.rmtree(目录, ignore_errors=True)

    def test_并入快照不重复计数(self):
        """交互模式整份重译时，同一处写法只能算一次。"""
        持久 = 内核.未定义报告(None)
        已计 = {}
        # 第一轮：缓冲里只有一行
        甲 = 内核.未定义报告(None)
        转译("核说（ascii（1））", 甲)
        已计 = 持久.并入快照(甲, 已计)
        self.assertEqual(持久.条目[("ascii", "内置函数")]["次数"], 1)
        # 第二轮：缓冲变成两行，整份重译 —— ascii 还是只出现 1 次
        乙 = 内核.未定义报告(None)
        转译("核说（ascii（1））\n核说（ascii（2））", 乙)
        已计 = 持久.并入快照(乙, 已计)
        self.assertEqual(
            持久.条目[("ascii", "内置函数")]["次数"], 2,
            "重译整份缓冲不能把上一轮的计数再加一遍",
        )


class 运行测试(unittest.TestCase):
    def setUp(self):
        self.目录 = tempfile.mkdtemp(prefix="核语言测试_")
        self.cwd = os.getcwd()
        os.chdir(self.目录)

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.目录, ignore_errors=True)

    def 运行(self, 源码, 输入=None):
        路径 = os.path.join(self.目录, "程序.xht")
        with open(路径, "w", encoding="utf-8") as f:
            f.write(源码)
        结果 = subprocess.run(
            [解释器, 内核脚本, 路径],
            input=(输入 or "").encode("utf-8"),
            capture_output=True,
            cwd=self.目录,
        )
        return (
            结果.returncode,
            结果.stdout.decode("utf-8", "replace"),
            结果.stderr.decode("utf-8", "replace"),
        )

    def test_你好世界(self):
        码, 输出, _ = self.运行('核说（"你好，世界！"）')
        self.assertEqual(码, 0)
        self.assertEqual(输出.strip(), "你好，世界！")

    def test_中文变量与循环(self):
        源码 = """
总数 = 0
核用 i 遍历 核数列（1, 11）：
    总数 = 总数 + i
核若 总数 == 55：
    核说（"对了", 总数）
核否则：
    核说（"错了"）
"""
        码, 输出, _ = self.运行(源码)
        self.assertEqual(码, 0)
        self.assertIn("对了 55", 输出)

    def test_输入输出(self):
        码, 输出, _ = self.运行('名字 = 说核（"名字："）\n核说（"你好", 名字）', 输入="小明\n")
        self.assertEqual(码, 0)
        self.assertIn("你好 小明", 输出)

    def test_函数递归(self):
        源码 = """
核定义 阶乘（n）：
    核若 n <= 1：
        核返回 1
    核否则：
        核返回 n * 阶乘（n - 1）
核说（阶乘（5））
"""
        码, 输出, _ = self.运行(源码)
        self.assertEqual(码, 0)
        self.assertEqual(输出.strip(), "120")

    def test_f字符串格式不变(self):
        码, 输出, _ = self.运行('平均 = 90\n核说（核"平均 {平均:.2f}"）')
        self.assertEqual(码, 0)
        self.assertEqual(输出.strip(), "平均 90.00")

    def test_语法错误行号(self):
        码, _, 错误 = self.运行("核说（1）\n核若 ：\n    核说（2）\n")
        self.assertEqual(码, 1)
        self.assertIn("第 2 行", 错误)
        self.assertIn("语法错误", 错误)

    def test_运行错误行号(self):
        码, _, 错误 = self.运行("核说（1）\n核说（1 / 0）\n")
        self.assertEqual(码, 1)
        self.assertIn("ZeroDivisionError", 错误)
        self.assertIn("第 2 行", 错误)
        self.assertIn("除数不能为 0", 错误)

    def test_未定义清单累积(self):
        路径 = os.path.join(self.目录, "程序.xht")
        with open(路径, "w", encoding="utf-8") as f:
            f.write('核说（ascii（1））\n核说（"x".casefold（））\n')
        for _ in range(2):
            subprocess.run([解释器, 内核脚本, 路径], capture_output=True, cwd=self.目录)
        清单 = os.path.join(self.目录, "未定义.txt")
        self.assertTrue(os.path.exists(清单))
        with open(清单, encoding="utf-8") as f:
            内容 = f.read()
        self.assertIn("ascii\t内置函数\t2", 内容)
        self.assertIn("casefold\t方法\t2", 内容)

    def test_未定义次数按真实出现计(self):
        # 同一个文件里出现两次，次数应为 2（而不是只记一次）
        路径 = os.path.join(self.目录, "多处.xht")
        with open(路径, "w", encoding="utf-8") as f:
            f.write('核说（ascii（1））\n核说（ascii（2））\n')
        subprocess.run([解释器, 内核脚本, 路径], capture_output=True, cwd=self.目录)
        清单 = os.path.join(self.目录, "未定义.txt")
        with open(清单, encoding="utf-8") as f:
            内容 = f.read()
        行 = [x for x in 内容.splitlines() if x.startswith("ascii\t")]
        self.assertTrue(行, msg="清单里应有 ascii 记录：\n%s" % 内容)
        次数 = 行[0].split("\t")[2]
        self.assertEqual(次数, "2", msg=行[0])

    def test_检查命令(self):
        路径 = os.path.join(self.目录, "好.xht")
        with open(路径, "w", encoding="utf-8") as f:
            f.write("核说（1）\n")
        结果 = subprocess.run(
            [解释器, 内核脚本, "检查", 路径], capture_output=True, cwd=self.目录
        )
        self.assertEqual(结果.returncode, 0)
        self.assertIn("检查通过", 结果.stdout.decode("utf-8", "replace"))

    def test_全角代码(self):
        码, 输出, _ = self.运行("核若 （１ ＜ ２）：\n    核说（“全角也能跑”）\n")
        self.assertEqual(码, 0)
        self.assertIn("全角也能跑", 输出)

    def test_管道输入不乱码(self):
        """通过管道输入中文，程序必须原样读到。

        打包成 exe 后 stdin 的编码是 gbk（跟随系统代码页），
        以前只有 运行文件() 调 准备输出()、没调 准备输入()，
        用户在核工坊里输入「小明」会变成「灏忔槑」。
        """
        码, 输出, _ = self.运行('名 = 说核()\n核说(核"你好，{名}")\n', 输入="小明\n")
        self.assertEqual(码, 0)
        self.assertIn("你好，小明", 输出)

    def test_输出是UTF8字节(self):
        """管道输出必须是 UTF-8 字节，不能是系统编码（gbk）。

        只在 exe 上暴露：打包入口直接调 命令行() 会绕过 准备输出()，
        输出的「核语言」是 GBK 字节 bacb d3ef，被当 UTF-8 读就是乱码。
        """
        路径 = os.path.join(self.目录, "编.xht")
        with open(路径, "w", encoding="utf-8") as f:
            f.write('核说("核语言")\n')
        结果 = subprocess.run(
            [解释器, 内核脚本, 路径], capture_output=True, cwd=self.目录,
            env=dict(os.environ, PYTHONIOENCODING="", PYTHONUTF8="0"),
        )
        输出 = 结果.stdout
        # 「核语言」的 UTF-8 字节是 e6a0 b8 e8af ad e8a8 80
        self.assertIn("核语言".encode("utf-8"), 输出,
                      "输出不是 UTF-8：%r" % 输出[:60])


class 示例测试(unittest.TestCase):
    """例子目录下的程序都要能跑通。"""

    def test_示例都能跑(self):
        目录 = os.path.join(根目录, "例子")
        for 名 in sorted(os.listdir(目录)):
            if not 名.endswith(".xht"):
                continue
            with self.subTest(文件=名):
                路径 = os.path.join(目录, 名)
                结果 = subprocess.run(
                    [解释器, 内核脚本, 路径],
                    input=b"85\n",
                    capture_output=True,
                    cwd=根目录,
                )
                self.assertEqual(
                    结果.returncode,
                    0,
                    msg=结果.stderr.decode("utf-8", "replace"),
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
