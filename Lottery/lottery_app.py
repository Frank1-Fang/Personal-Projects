# -*- coding: utf-8 -*-

import sys
import os
import random
import datetime as dt
import pandas as pd
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QAction, QPainter
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog,
    QHBoxLayout, QSpinBox, QTextEdit, QMessageBox, QFrame
)

MASK_CHAR = "*"


def mask_phone(p: str) -> str:
    """脱敏手机号: 保留前三后四，中间用****代替"""
    s = ''.join(ch for ch in str(p) if ch.isdigit())
    if len(s) >= 7:
        return s[:3] + MASK_CHAR * 4 + s[-4:]
    if len(s) > 4:
        head = s[:2]
        tail = s[-2:]
        return head + MASK_CHAR * max(2, len(s) - 4) + tail
    return s


class LotteryApp(QWidget):
    def __init__(self, background_path: str | None = None):
        super().__init__()
        self.setWindowTitle("抽奖程序")

        # 启动时最大化
        # 标题栏：保留最小化、最大化、关闭
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowMinimizeButtonHint |
            Qt.WindowMaximizeButtonHint |
            Qt.WindowCloseButtonHint
        )

        #self.showMaximized()
        #QTimer.singleShot(100, self.lock_size)

        # 已经加载背景图
        self._bg_pix = QPixmap(background_path) if (background_path and os.path.exists(background_path)) else None

        self.df_all: pd.DataFrame | None = None
        self.df_winners: pd.DataFrame | None = None

        # 滚动效果
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._roll)
        self.is_rolling = False

        self._build_ui()

        self.showMaximized()
        QTimer.singleShot(100, self.lock_size)

    def lock_size(self):
        """锁定当前窗口大小"""
        self.setFixedSize(self.size())

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # === 背景图区域 ===
        self.bg_frame = QFrame(self)
        self.bg_frame.setStyleSheet("QFrame { background: transparent; }")

        bg_layout = QVBoxLayout(self.bg_frame)
        bg_layout.setContentsMargins(0, 0, 0, 0)  # 先置 0，resizeEvent 时再动态调整
        bg_layout.setSpacing(0)

        self.status_label = QLabel("请开始抽奖", self.bg_frame)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 24px; font-weight: bold; color: red;")
        bg_layout.addWidget(self.status_label)

        self.text = QTextEdit(self.bg_frame)
        self.text.setReadOnly(True)
        self.text.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 22px; background: transparent;"  # ← 调节号码字体大小
        )
        bg_layout.addWidget(self.text)

        root.addWidget(self.bg_frame, 9)

        # === 工具栏 ===
        self.toolbar_frame = QFrame(self)
        self.toolbar_frame.setFixedHeight(50)
        self.toolbar_frame.setStyleSheet("QFrame { background: white; }")
        toolbar_layout = QHBoxLayout(self.toolbar_frame)
        toolbar_layout.setContentsMargins(24, 6, 24, 6)
        toolbar_layout.setSpacing(12)

        btn_open = QPushButton("选择号码表 (Excel)")
        btn_open.clicked.connect(self.choose_excel)
        self.lbl_total = QLabel("未选择文件")
        lbl_count = QLabel("抽取人数：")
        self.spin_count = QSpinBox()
        self.spin_count.setRange(1, 1000000)
        self.spin_count.setValue(100)

        self.btn_draw = QPushButton("开始抽奖")
        self.btn_draw.setEnabled(False)
        self.btn_draw.clicked.connect(self.toggle_draw)

        self.btn_export = QPushButton("导出Excel")
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self.export_excel)

        toolbar_layout.addWidget(btn_open)
        toolbar_layout.addSpacing(12)
        toolbar_layout.addWidget(self.lbl_total)
        toolbar_layout.addStretch(1)
        toolbar_layout.addWidget(lbl_count)
        toolbar_layout.addWidget(self.spin_count)
        toolbar_layout.addSpacing(12)
        toolbar_layout.addWidget(self.btn_draw)
        toolbar_layout.addWidget(self.btn_export)

        root.addWidget(self.toolbar_frame, 0)


    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.bg_frame:
            w = self.bg_frame.width()
            h = self.bg_frame.height()
            left   = int(w * 0.1)   # 左边距 = 宽度的 12%
            top    = int(h * 0.30)   # 上边距 = 高度的 30%
            right  = int(w * 0.1)   # 右边距 = 宽度的 12%
            bottom = int(h * 0.15)   # 下边距 = 高度的 15%
            self.bg_frame.layout().setContentsMargins(left, top, right, bottom)


    def paintEvent(self, e):
        if self._bg_pix:
            painter = QPainter(self)
            rect = self.bg_frame.geometry()
            painter.drawPixmap(
                rect,
                self._bg_pix.scaled(
                    rect.size(),
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation
                )
            )

    def choose_excel(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择号码表 Excel 文件", ".", "Excel (*.xlsx *.xls)")
        if not path:
            return
        try:
            df = pd.read_excel(path)
        except Exception as e:
            QMessageBox.critical(self, "读取失败", f"无法读取 Excel：\n{e}")
            return

        col = "Numbers" if "Numbers" in df.columns else df.columns[0]
        s = df[col].dropna().astype(str).map(lambda x: ''.join(ch for ch in x if ch.isdigit()))
        self.df_all = pd.DataFrame({"Phone": s.unique()})
        total = len(self.df_all)
        self.lbl_total.setText(f"已载入：{os.path.basename(path)}（{total} 条号码）")
        self.btn_draw.setEnabled(total > 0)
        self.btn_export.setEnabled(False)
        self.text.clear()
        self.df_winners = None

    def draw(self):
        if self.df_all is None or self.df_all.empty:
            QMessageBox.warning(self, "未载入", "请先载入号码 Excel 文件")
            return
        n = self.spin_count.value()
        total = len(self.df_all)
        if n > total:
            n = total

        idx = random.sample(range(total), n)
        winners = self.df_all.iloc[idx].copy()
        winners["Masked"] = winners["Phone"].map(mask_phone)
        self.df_winners = winners.reset_index(drop=True)

        masked_list = winners["Masked"].tolist()
        cols = 7  # ← 调节号码列数
        lines = []
        for i in range(0, len(masked_list), cols):
            lines.append("  ".join(masked_list[i:i + cols]))
        self.text.setPlainText("\n".join(lines))
        self.btn_export.setEnabled(True)

    def export_excel(self):
        if self.df_winners is None or self.df_winners.empty:
            QMessageBox.information(self, "无结果", "请先抽奖，再导出。")
            return
        ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"抽奖结果_{ts}.xlsx"
        path, _ = QFileDialog.getSaveFileName(self, "保存结果为 Excel", default_name, "Excel (*.xlsx)")
        if not path:
            return
        try:
            self.df_winners[["Phone"]].to_excel(path, index=False, header=False)
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"导出失败：\n{e}")
            return
        QMessageBox.information(self, "完成", f"已导出：\n{path}")

    # 滚动功能
    def toggle_draw(self):
        if not self.is_rolling:
            if self.df_all is None or self.df_all.empty:
                QMessageBox.warning(self, "未载入", "请先载入号码 Excel 文件")
                return
            self.is_rolling = True
            self.status_label.setText("抽奖中...")   # 🔑 显示提示
            self.btn_draw.setText("停止抽奖")
            self.timer.start(50)
        else:
            self.is_rolling = False
            self.btn_draw.setText("开始抽奖")
            self.timer.stop()
            self._finalize_winners()

    def _roll(self):
        n = self.spin_count.value()
        total = len(self.df_all)
        idx = random.sample(range(total), min(n, total))
        winners = self.df_all.iloc[idx].copy()
        winners["Masked"] = winners["Phone"].map(mask_phone)
        masked_list = winners["Masked"].tolist()

        while len(masked_list) < 200:
            # 从所有号码中随机选一个补充（避免太单调）
            rand_idx = random.randint(0, total - 1)
            masked_list.append(mask_phone(self.df_all.iloc[rand_idx]["Phone"]))

        cols = 7  # ← 调节号码列数
        lines = []
        for i in range(0, len(masked_list), cols):
            lines.append("  ".join(masked_list[i:i + cols]))
        self.text.setPlainText("\n".join(lines))

    def _finalize_winners(self):
        n = self.spin_count.value()
        total = len(self.df_all)
        idx = random.sample(range(total), min(n, total))
        winners = self.df_all.iloc[idx].copy()
        winners["Masked"] = winners["Phone"].map(mask_phone)
        self.df_winners = winners.reset_index(drop=True)

        masked_list = winners["Masked"].tolist()
        cols = 7  # ← 调节号码列数
        lines = []
        for i in range(0, len(masked_list), cols):
            lines.append("  ".join(masked_list[i:i + cols]))
        self.text.setPlainText("\n".join(lines))
        self.status_label.setText("抽奖结果")
        self.btn_export.setEnabled(True)

def resource_path(relative_path):
        """获取资源文件的绝对路径（兼容 PyInstaller 打包后）"""
        if hasattr(sys, '_MEIPASS'):  # 打包后临时目录
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path)


def main():
    bg = resource_path("background.jpg")  # ← 用资源路径获取图片
    app = QApplication(sys.argv)
    w = LotteryApp(background_path=bg)
    w.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
