# -*- coding: utf-8 -*-
"""由 素材/核图标.png 生成各类尺寸的图标文件。

用法：
    python 测试/生成图标.py

产物：
    素材/核图标.png          透明背景主图（保持原样）
    素材/核图标.ico          Windows 多尺寸图标（窗口 / 任务栏）
    素材/核图标_16.png 等    各尺寸 PNG（文档、网页用）
"""

import os
import sys

这里 = os.path.dirname(os.path.abspath(__file__))
根目录 = os.path.dirname(这里)
素材 = os.path.join(根目录, "素材")
主图 = os.path.join(素材, "核图标.png")

尺寸集 = (16, 24, 32, 48, 64, 128, 256)


def 主():
    try:
        from PIL import Image
    except ImportError:
        print("需要 Pillow：pip install pillow")
        return 1
    if not os.path.exists(主图):
        print("找不到 %s" % 主图)
        return 1

    图 = Image.open(主图).convert("RGBA")
    已存在 = 0
    for 边 in 尺寸集:
        副本 = 图.copy()
        副本.thumbnail((边, 边), Image.LANCZOS)
        画布 = Image.new("RGBA", (边, 边), (0, 0, 0, 0))
        画布.paste(副本, ((边 - 副本.width) // 2, (边 - 副本.height) // 2), 副本)
        路径 = os.path.join(素材, "核图标_%d.png" % 边)
        画布.save(路径)
        已存在 += 1
        print("  %s" % os.path.basename(路径))

    图.save(
        os.path.join(素材, "核图标.ico"),
        sizes=[(边, 边) for 边 in 尺寸集],
    )
    print("  核图标.ico")
    print("共写出 %d 个文件" % (已存在 + 1))
    return 0


if __name__ == "__main__":
    sys.exit(主())
