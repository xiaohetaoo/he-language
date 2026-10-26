# -*- coding: utf-8 -*-
"""Qt 版打包入口。"""
import os
import sys

这里 = os.path.dirname(os.path.abspath(__file__))
if 这里 not in sys.path:
    sys.path.insert(0, 这里)

def 主():
    基 = getattr(sys, '_MEIPASS', 这里)
    for 子 in ('', '素材'):
        目录 = os.path.join(基, 子) if 子 else 基
        if os.path.isdir(目录) and 目录 not in sys.path:
            sys.path.insert(0, 目录)
    参数 = sys.argv[1:]
    if 参数 and 参数[0] == '--自检界面':
        目录 = 参数[1] if len(参数) > 1 else '.'
        return _自检(目录)
    if 参数 and 参数[0] == '--内核':
        # 作为解释器运行用户程序：exe 自带内核，目标机器无需 Python
        # 必须走 主入口()，它内部会调 准备输出()/准备输入()。
        # 直接调 命令行() 会绕过这两个：exe 里 stdin 是 gbk，
        # 用户中文输入会变成乱码（「小明」→「灏忔槑」）；
        # stdout 也保持系统编码，管道读取时同样是乱码。
        import 核
        sys.argv = ['核'] + 参数[1:]
        return 核.主入口()
    import 核工坊Qt
    return 核工坊Qt.启动()

def _自检(输出目录):
    import json, time
    from PySide6.QtWidgets import QApplication, QLabel as _QLabel
    import 核工坊Qt, 核
    基 = getattr(sys, '_MEIPASS', 这里)
    os.makedirs(输出目录, exist_ok=True)
    应用 = QApplication([])
    窗 = 核工坊Qt.主窗()
    窗.show()
    import time as _t
    截止 = _t.time() + 3.0
    while _t.time() < 截止:
        应用.processEvents()
        _t.sleep(0.02)
    报告 = {
        '运行方式': 'Qt 打包 exe',
        '界面版本': 核.版本,
        '顶行': 窗.顶行.项目名.text(),
        '竖条按钮': list(窗.竖条.钮们),
        '竖条图标齐全': all(not b.pixmap().isNull() for b in 窗.竖条.钮们.values()),
        '顶行有设置': any('设置' in c.toolTip() for c in 窗.顶行.findChildren(_QLabel)),
        '标签数': 窗.标签栏.count(),
        '图标存在': os.path.exists(os.path.join(基, '素材', '核图标.ico')),
        '对照表行数': len(窗.对照.toPlainText().splitlines()),
        '启动字号': 窗.字号,
    }
    # 字号必须真的改变渲染尺寸（QSS 优先级坑）：
    # 打包后如果 QSS 里的 font-size 占位符没被替换，
    # 行高会恒等于 16，用户改字号看不到任何变化。
    try:
        _编 = 窗.当前
        窗.设字号(10)
        应用.processEvents()
        _小 = _编.fontMetrics().height()
        窗.设字号(20)
        应用.processEvents()
        _大 = _编.fontMetrics().height()
        报告['字号行高_10pt'] = _小
        报告['字号行高_20pt'] = _大
        报告['字号真的生效'] = bool(_大 > _小)
        报告['行号跟随字号'] = bool(
            _编.行号.fontMetrics().height() == _大)
        窗.设字号(12)
        应用.processEvents()
        报告['恢复后字号'] = 窗.字号
    except Exception as e:
        报告['字号检查失败'] = str(e)
    # 0.0.12 起：帮助与版本控制是运行时 import 的，静态分析扫不到，
    # 打包时若漏了 --hidden-import，这里就会暴露出来（ModuleNotFoundError）。
    for _名, _模块 in (('帮助窗口', None), ('版本控制', None),
                       ('版本控制窗口', None)):
        try:
            __import__(_名)
            报告['模块_' + _名] = True
        except Exception as e:
            报告['模块_' + _名] = '导入失败：%s' % e
    try:
        import 版本控制
        # 用主窗的真实项目目录判断（打包版会自动上移一级，见 _默认项目目录）
        _项目 = 窗.项目目录
        报告['版本控制_探测目录'] = _项目
        报告['版本控制可用'] = bool(版本控制.状态(_项目).get('可用'))
    except Exception as e:
        报告['版本控制可用'] = '检查失败：%s' % e
    try:
        import 帮助窗口
        # 版本历史读的是项目目录里的 版本/，和用户实际点开时一致
        报告['读到归档版本数'] = len(帮助窗口.已归档版本(窗.项目目录))
    except Exception as e:
        报告['读到归档版本数'] = '失败：%s' % e
    try:
        窗.打开说明文档()
        应用.processEvents()
        报告['打开说明文档'] = 窗.标签栏.count() > 1
    except Exception as e:
        报告['打开说明文档'] = '失败：%s' % e
    try:
        _编2 = 窗.当前
        _编2.置文本('核定义 f()：\n    核说(1)\n核说(2)\n')
        _块 = _编2.document().findBlockByNumber(0)
        报告['折叠可用'] = bool(_编2.可折叠(_块))
        if _编2.可折叠(_块):
            _编2.切换折叠(_块)
            应用.processEvents()
            报告['折叠真的生效'] = not _编2.document().findBlockByNumber(1).isVisible()
            _编2.全部展开()
    except Exception as e:
        报告['折叠可用'] = '失败：%s' % e
    try:
        窗.grab().save(os.path.join(输出目录, '自检_Qt.png'))
    except Exception as e:
        报告['截图失败'] = str(e)
    with open(os.path.join(输出目录, '自检报告.json'), 'w', encoding='utf-8') as f:
        json.dump(报告, f, ensure_ascii=False, indent=2)
    print(json.dumps(报告, ensure_ascii=False, indent=2))
    应用.quit()
    return 0

if __name__ == '__main__':
    sys.exit(主())
