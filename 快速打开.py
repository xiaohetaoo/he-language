# -*- coding: utf-8 -*-
"""快速打开文件对话框（类似 PyCharm 的 Search Everywhere）。

在项目目录里按文件名**子序列模糊匹配**，回车打开。

匹配规则（P2-18）：这是**子序列**匹配，词里的字符必须按顺序出现、
可以不连续 —— 输入 `rdm` 能命中 `README.md`，输入 `xht` 能命中
`未命名.xht`。以前文档写「模糊匹配」，实际只做了 `词 in 名` 的子串判断，
`rdm` 一条都匹配不上，与宣传不符。
排名同时奖励「连续命中的多」和「命中位置靠前」。
"""

import os

from PySide6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout,
)

import 主题

跳过目录 = {"__pycache__", "build", "dist", "版本", ".git", ".idea", ".vscode"}
跳过后缀 = (".pyc", ".pkg", ".pyz", ".toc", ".exe", ".zip")


def _子序列得分(词, 文):
    """词是不是 文 的子序列？是则返回得分（越大越好），否则返回 None。

    得分同时奖励「连续命中」和「命中靠前」：
      每命中一个字符 +10；与前一个命中相邻再 +8；
      起始位置越靠前越好（每靠后一格 -0.2）。
    """
    if not 词:
        return 0.0
    分 = 0.0
    上 = -2
    起 = -1
    i = 0
    for 序, 字 in enumerate(文):
        if 字 != 词[i]:
            continue
        if 起 < 0:
            起 = 序
        分 += 10.0
        if 序 == 上 + 1:
            分 += 8.0
        上 = 序
        i += 1
        if i == len(词):
            return 分 - 起 * 0.2
    return None


class 快速打开(QDialog):
    def __init__(self, 主窗):
        super().__init__(主窗)
        self.主窗 = 主窗
        self.setWindowTitle("快速打开")
        self.setModal(True)
        self.resize(560, 420)
        self.setStyleSheet(主窗.styleSheet())
        # 主窗换主题时由 核工坊Qt.主窗._同步对话框样式 重新套一遍
        self.跟主题 = True

        self.全部文件 = self._收集(主窗.项目目录)
        self.候选 = list(self.全部文件)

        布局 = QVBoxLayout(self)
        布局.setContentsMargins(主题.内边距, 主题.内边距, 主题.内边距, 主题.内边距)
        布局.setSpacing(主题.间距)

        self.输入框 = QLineEdit()
        self.输入框.setObjectName("输入框")
        self.输入框.setPlaceholderText("输入文件名过滤，回车打开，Esc 关闭")
        self.输入框.textChanged.connect(self._过滤)
        self.输入框.returnPressed.connect(self._打开选中)
        布局.addWidget(self.输入框)

        self.列表 = QListWidget()
        # 行高收到 24px（P2-18）。默认继承主题里的 padding 后每行 31px，
        # 420px 高的窗口只能放十来行，找个文件要滚半天。
        self.列表.setStyleSheet(
            "QListWidget::item { min-height: 22px; padding: 0px 6px; }")
        self.列表.itemActivated.connect(lambda _: self._打开选中())
        布局.addWidget(self.列表, 1)

        # 底部说明用 QLabel（P2-18）。以前是 setReadOnly(True) 的 QLineEdit：
        # 长得像输入框、能点进去选中文字，用户会以为「这里也能打字过滤」，
        # 敲了半天没反应才发现上面那个才是输入框。
        self.提示 = QLabel("")
        self.提示.setObjectName("crumb")
        布局.addWidget(self.提示)

        self._过滤("")
        self.输入框.setFocus()

    def _收集(self, 根):
        结果 = []
        for 目录, 子目录, 文件 in os.walk(根):
            子目录[:] = [d for d in 子目录 if d not in 跳过目录 and not d.startswith(".")]
            for 名 in 文件:
                if 名.startswith(".") or 名.endswith(跳过后缀):
                    continue
                # 下划线开头的是内部文件（_启动Qt.py、_忽略.py 之类），
                # 不是给用户打开的入口，列出来只会干扰（P2-18）。
                if 名.startswith("_"):
                    continue
                if not 名.endswith((".xht", ".py", ".md", ".txt", ".json")):
                    continue
                全 = os.path.join(目录, 名)
                结果.append((os.path.relpath(全, 根), 全))
        return sorted(结果, key=lambda x: x[0].lower())

    def _过滤(self, 词):
        词 = 词.strip().lower()
        self.列表.clear()
        if not 词:
            self.候选 = self.全部文件[:200]
        else:
            # 真·子序列模糊匹配：文件名里命中排前面，路径里命中排后面。
            命中 = []
            for 相对, 全 in self.全部文件:
                名 = os.path.basename(相对).lower()
                分 = _子序列得分(词, 名)
                if 分 is not None:
                    命中.append((-分, 0, 相对, 全))
                    continue
                分 = _子序列得分(词, 相对.lower())
                if 分 is not None:
                    命中.append((-分, 1, 相对, 全))
            命中.sort()
            self.候选 = [(r, p) for _, _, r, p in 命中[:200]]
        for 相对, _全 in self.候选:
            QListWidgetItem(相对, self.列表)
        if self.列表.count():
            self.列表.setCurrentRow(0)
        self.提示.setText(
            "共 %d 个文件，匹配 %d 个" % (len(self.全部文件), len(self.候选))
        )

    def _打开选中(self):
        项 = self.列表.currentItem()
        if 项 is None:
            return
        相对 = 项.text()
        for 相对路径, 全 in self.候选:
            if 相对路径 == 相对:
                self.主窗.打开(全)
                # close() 让 exec() 正常返回，再交给事件循环回收。
                # 直接 destroy() 在模态循环里可能卡住。
                self.close()
                self.deleteLater()
                return
