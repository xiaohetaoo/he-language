# -*- coding: utf-8 -*-
"""查找 / 替换 对话框（Qt 版）。"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QVBoxLayout,
)


class 查找对话框(QDialog):
    """非模态的查找替换框，像 PyCharm 那样停在编辑器上方。"""

    def __init__(self, 主窗, 编辑器):
        super().__init__(主窗)
        self.主窗 = 主窗
        self.编辑器 = 编辑器
        self.setWindowTitle("查找 / 替换")
        self.setModal(False)
        self.resize(440, 150)
        self.setStyleSheet(主窗.styleSheet())
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)

        if 编辑器 is not None:
            游 = 编辑器.textCursor()
            if 游.hasSelection():
                self._初选 = 游.selectedText()

        self._建界面()

    def _建界面(self):
        布局 = QVBoxLayout(self)
        布局.setContentsMargins(16, 14, 16, 12)
        布局.setSpacing(8)

        网 = QGridLayout()
        网.setHorizontalSpacing(8)
        网.setVerticalSpacing(8)

        网.addWidget(QLabel("查找"), 0, 0)
        self.查找框 = QLineEdit()
        self.查找框.setObjectName("输入框")
        self.查找框.returnPressed.connect(self.查找下一个)
        网.addWidget(self.查找框, 0, 1)

        网.addWidget(QLabel("替换"), 1, 0)
        self.替换框 = QLineEdit()
        self.替换框.setObjectName("输入框")
        self.替换框.returnPressed.connect(self.替换当前)
        网.addWidget(self.替换框, 1, 1)

        钮列 = QVBoxLayout()
        钮列.setSpacing(4)
        for 文本, 槽 in (
            ("查找下一个", self.查找下一个),
            ("替换", self.替换当前),
            ("全部替换", self.全部替换),
        ):
            钮 = QPushButton(文本)
            # 不设 autoDefault：否则对话框显示时 Qt 会把「默认按钮」
            # 转给其中一个，回车键就去执行它，而不是用户以为的那个动作。
            钮.setAutoDefault(False)
            钮.clicked.connect(槽)
            钮列.addWidget(钮)
        网.addLayout(钮列, 0, 2, 2, 1)

        布局.addLayout(网)

        行 = QHBoxLayout()
        self.勾区分 = QCheckBox("区分大小写")
        行.addWidget(self.勾区分)
        行.addStretch(1)
        self.计数 = QLabel("")
        # 用 objectName 交给 QSS，而不是行内写死颜色：
        # 行内颜色在换主题时不会更新（浅底上会变成看不清的浅灰）。
        self.计数.setObjectName("hintText")
        行.addWidget(self.计数)
        关 = QPushButton("关闭")
        关.setAutoDefault(False)
        关.clicked.connect(self.close)
        行.addWidget(关)
        布局.addLayout(行)

        if getattr(self, "_初选", ""):
            self.查找框.setText(self._初选)
            self.查找框.selectAll()
        self.查找框.setFocus()

    def _当前编辑器(self):
        if self.主窗.当前 is not None:
            self.编辑器 = self.主窗.当前
        return self.编辑器

    def 查找下一个(self):
        编 = self._当前编辑器()
        if 编 is None:
            return
        词 = self.查找框.text()
        if not 词:
            return
        if 编.查找下一个(词, self.勾区分.isChecked()):
            self.计数.setText("已定位")
        else:
            self.计数.setText("没找到")

    def 替换当前(self):
        编 = self._当前编辑器()
        if 编 is None:
            return
        词 = self.查找框.text()
        if not 词:
            return
        if 编.替换当前(词, self.替换框.text()):
            self.计数.setText("已替换 1 处")
            self.查找下一个()
        else:
            self.计数.setText("没找到")

    def 全部替换(self):
        编 = self._当前编辑器()
        if 编 is None:
            return
        词 = self.查找框.text()
        if not 词:
            return
        次数 = 编.全部替换(词, self.替换框.text())
        self.计数.setText("已替换 %d 处" % 次数)


class 跳转对话框(QDialog):
    """转到指定行。"""

    def __init__(self, 主窗, 编辑器):
        super().__init__(主窗)
        self.主窗 = 主窗
        self.编辑器 = 编辑器
        self.setWindowTitle("转到行")
        self.setModal(True)
        self.resize(260, 90)
        self.setStyleSheet(主窗.styleSheet())

        布局 = QHBoxLayout(self)
        布局.setContentsMargins(16, 14, 16, 14)
        布局.addWidget(QLabel("行号"))
        self.框 = QLineEdit()
        self.框.setObjectName("输入框")
        self.框.returnPressed.connect(self.跳)
        布局.addWidget(self.框, 1)
        钮 = QPushButton("跳转")
        # 这是本对话框唯一的主动作，明确标成主按钮；
        # autoDefault 关掉，免得被 Qt 换成别的按钮抢走回车。
        钮.setAutoDefault(False)
        钮.setDefault(True)
        钮.setProperty("primary", "true")
        钮.clicked.connect(self.跳)
        布局.addWidget(钮)

        if 编辑器 is not None:
            行, _ = 编辑器.当前行列()
            self.框.setText(str(行))
            self.框.selectAll()

    def 跳(self):
        try:
            行 = int(self.框.text())
        except ValueError:
            return
        if self.编辑器 is not None and self.编辑器.跳到行(行):
            # close() 结束模态循环；deleteLater() 交给事件循环回收。
            # 直接 destroy() 在 exec() 里可能让循环拿不到返回值而卡住。
            self.close()
            self.deleteLater()
