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
            "核说（sum（[1, 2]））\n核说（type（1））\n“x”.capitalize（）\n核说（1, file=核空）",
            报告,
        )
        类别 = set(报告.条目)
        self.assertIn(("sum", "内置函数"), 类别)
        self.assertIn(("type", "内置函数"), 类别)
        self.assertIn(("capitalize", "方法"), 类别)
        self.assertIn(("file", "参数名"), 类别)

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
        报告 = 内核.未定义报告(None)
        转译("len = 3\n核说（len）\n核说（sum）", 报告)
        self.assertEqual(list(报告.条目), [("sum", "内置函数")])


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
            f.write('核说（sum（[1, 2]））\n核说（"x".capitalize（））\n')
        for _ in range(2):
            subprocess.run([解释器, 内核脚本, 路径], capture_output=True, cwd=self.目录)
        清单 = os.path.join(self.目录, "未定义.txt")
        self.assertTrue(os.path.exists(清单))
        with open(清单, encoding="utf-8") as f:
            内容 = f.read()
        self.assertIn("sum\t内置函数\t2", 内容)
        self.assertIn("capitalize\t方法\t2", 内容)

    def test_未定义次数按真实出现计(self):
        # 同一个文件里出现两次，次数应为 2（而不是只记一次）
        路径 = os.path.join(self.目录, "多处.xht")
        with open(路径, "w", encoding="utf-8") as f:
            f.write("核说（sum（[1]））\n核说（sum（[2]））\n")
        subprocess.run([解释器, 内核脚本, 路径], capture_output=True, cwd=self.目录)
        清单 = os.path.join(self.目录, "未定义.txt")
        with open(清单, encoding="utf-8") as f:
            内容 = f.read()
        行 = [x for x in 内容.splitlines() if x.startswith("sum\t")]
        self.assertTrue(行, msg="清单里应有 sum 记录：\n%s" % 内容)
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
