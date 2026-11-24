# -*- coding: utf-8 -*-
"""保存时的行尾保真：CRLF 文件不能被悄悄改成 LF。

编辑器内部一律 LF（QPlainTextEdit 只认 \n），但写回磁盘必须按
文件原本的行尾。以前固定 newline="\n"：在 Windows 上打开 CRLF 的
.xht，改一个字保存，整个文件行尾全变 —— git diff 显示「每行都改了」。
本仓库 .gitattributes 明确容忍 CRLF（cr-at-eol），这种改写是实打实的噪声。

用法：python 测试/查行尾.py
"""
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
目录 = tempfile.mkdtemp(prefix="核行尾_")
os.environ["核工坊_配置目录"] = 目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication

应用 = QApplication.instance() or QApplication([])
import 核工坊Qt

窗 = 核工坊Qt.主窗()
坏 = []


def 检(条件, 说明):
    print(("  ok   " if 条件 else "  !!   ") + 说明)
    if not 条件:
        坏.append(说明)


def 字节(路径):
    with open(路径, "rb") as f:
        return f.read()


print("== 一、CRLF 文件改一个字再保存，行尾不许变 ==")
p = os.path.join(目录, "甲.xht")
with open(p, "wb") as f:
    f.write('核说("甲")\r\n核说("乙")\r\n'.encode("utf-8"))
前 = 字节(p)
编 = 窗.打开(p)
检(getattr(编, "行尾", None) == "\r\n", "打开时认出 CRLF")
编.置文本('核说("甲甲")\n核说("乙")\n')
编.已改 = True
检(窗.保存(编, 弹窗=False), "保存成功")
后 = 字节(p)
检(后 == '核说("甲甲")\r\n核说("乙")\r\n'.encode("utf-8"),
   "写回去仍是 CRLF（实际 %r）" % 后)
检(b"\r\r\n" not in 后, "没有变成 CRCRLF")

print("== 二、LF 文件保持 LF ==")
q = os.path.join(目录, "乙.xht")
with open(q, "wb") as f:
    f.write('核说("丙")\n核说("丁")\n'.encode("utf-8"))
编2 = 窗.打开(q)
检(getattr(编2, "行尾", None) == "\n", "打开时认出 LF")
编2.置文本('核说("丙丙")\n核说("丁")\n')
编2.已改 = True
窗.保存(编2, 弹窗=False)
检(字节(q) == '核说("丙丙")\n核说("丁")\n'.encode("utf-8"), "写回去仍是 LF")

print("== 三、状态栏把行尾说出来 ==")
窗._显示文档(编)
窗.更新状态栏()
检("CRLF" in 窗.状态右.text(), "CRLF 文档状态栏显示 CRLF（实际 %r）" % 窗.状态右.text())
窗._显示文档(编2)
窗.更新状态栏()
检("LF" in 窗.状态右.text() and "CRLF" not in 窗.状态右.text(),
   "LF 文档状态栏显示 LF（实际 %r）" % 窗.状态右.text())

print("== 四、外部改成 CRLF 后重新加载，行尾跟着更新 ==")
with open(q, "wb") as f:
    f.write('核说("戊")\r\n'.encode("utf-8"))
窗._重新加载(编2, q)
检(getattr(编2, "行尾", None) == "\r\n", "重新加载后认出新行尾")

print("== 五、GBK + CRLF 一起保住 ==")
r = os.path.join(目录, "丙.xht")
with open(r, "wb") as f:
    f.write('核说("中文")\r\n'.encode("gbk"))
编3 = 窗.打开(r)
检(编3.编码.lower().startswith("gbk") and 编3.行尾 == "\r\n", "认出 GBK + CRLF")
编3.置文本('核说("中文文")\n')
编3.已改 = True
窗.保存(编3, 弹窗=False)
检(字节(r) == '核说("中文文")\r\n'.encode("gbk"), "GBK 与 CRLF 都没变")

print()
print("行尾保真：%d 处问题" % len(坏))
sys.exit(1 if 坏 else 0)
