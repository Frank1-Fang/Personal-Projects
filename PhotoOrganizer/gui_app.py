# gui_app.py
import sys
from pathlib import Path
from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Signal, QObject, QThread
from PySide6.QtGui import QTextCursor, QPixmap

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from photo_organizer.organizer import organize_photos


class EmittingStream(QObject):
    text_emitted = Signal(str)

    def write(self, text: str):
        if text:
            for line in text.splitlines(True):
                self.text_emitted.emit(line)

    def flush(self):
        pass


# --- 后台工作线程 ---
class OrganizeWorker(QThread):
    log = Signal(str)
    done = Signal(int)     # 0=success, 1=error
    error = Signal(str)
    progress = Signal(int)

    review_ready = Signal(list)  # 处理结束后的分组数据

    def __init__(self, input_dir: Path, output_dir: Path, dup_dir: Path, parent=None):
        super().__init__(parent)
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.dup_dir = dup_dir

    def run(self):
        import sys as _sys
        # 备份 stdout/stderr
        old_stdout, old_stderr = _sys.stdout, _sys.stderr
        out_stream, err_stream = EmittingStream(), EmittingStream()
        out_stream.text_emitted.connect(self.log.emit)
        err_stream.text_emitted.connect(self.log.emit)

        try:
            _sys.stdout, _sys.stderr = out_stream, err_stream
            review_groups = organize_photos(
                self.input_dir, self.output_dir, self.dup_dir,
                progress_callback=lambda *args: self.progress.emit(args[0])
            )
            if review_groups is None:
                review_groups = []
            self.review_ready.emit(review_groups)
            self.done.emit(0)
        except Exception as e:
            # 直接把异常消息打到日志
            self.error.emit(str(e))
            self.done.emit(1)
        finally:
            _sys.stdout, _sys.stderr = old_stdout, old_stderr


# --- 主窗口 ---
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PhotoOrganizer GUI")
        self.resize(900, 600)

        # 控件
        self.input_edit = QtWidgets.QLineEdit()
        self.output_edit = QtWidgets.QLineEdit()
        self.dup_edit = QtWidgets.QLineEdit()
        self.btn_input = QtWidgets.QPushButton("Browse...")
        self.btn_output = QtWidgets.QPushButton("Browse...")
        self.btn_dup = QtWidgets.QPushButton("Browse...")
        self.run_btn = QtWidgets.QPushButton("Run")
        self.review_btn = QtWidgets.QPushButton("Review Duplicates") # Review duplicates
        self.review_btn.setEnabled(False)
        self.progress = QtWidgets.QProgressBar()
        self.progress.setTextVisible(False)
        self.log_view = QtWidgets.QTextEdit()
        self.log_view.setReadOnly(True)
        self.status_label = QtWidgets.QLabel("Ready")

        # 布局
        form = QtWidgets.QFormLayout()
        row1 = QtWidgets.QHBoxLayout()
        row1.addWidget(self.input_edit)
        row1.addWidget(self.btn_input)
        form.addRow("Input folder:", row1)

        row2 = QtWidgets.QHBoxLayout()
        row2.addWidget(self.output_edit)
        row2.addWidget(self.btn_output)
        form.addRow("Output folder:", row2)

        row3 = QtWidgets.QHBoxLayout()
        row3.addWidget(self.dup_edit)
        row3.addWidget(self.btn_dup)
        form.addRow("Duplicates folder:", row3)

        top_box = QtWidgets.QGroupBox("Folders")
        top_box.setLayout(form)

        btn_bar = QtWidgets.QHBoxLayout()
        btn_bar.addWidget(self.run_btn)
        btn_bar.addWidget(self.review_btn) # Review button
        btn_bar.addStretch(1)
        btn_bar.addWidget(self.progress)

        central = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(central)
        v.addWidget(top_box)
        v.addLayout(btn_bar)
        v.addWidget(self.log_view)
        v.addWidget(self.status_label)
        self.setCentralWidget(central)

        # 信号槽
        self.btn_input.clicked.connect(lambda: self.pick_dir(self.input_edit))
        self.btn_output.clicked.connect(lambda: self.pick_dir(self.output_edit))
        self.btn_dup.clicked.connect(lambda: self.pick_dir(self.dup_edit))
        self.run_btn.clicked.connect(self.start_run)

        self.review_btn.clicked.connect(self.open_review) # Open review

        self.worker = None  # type: OrganizeWorker | None

        self.last_groups = []

    # 选择文件夹
    def pick_dir(self, line_edit: QtWidgets.QLineEdit):
        d = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Folder")
        if d:
            line_edit.setText(d)

    # 启动任务
    def start_run(self):
        if self.worker and self.worker.isRunning():
            QtWidgets.QMessageBox.information(self, "Running", "A task is already running.")
            return
        
        # 读取原始文本，空值校验
        in_raw  = self.input_edit.text().strip()
        out_raw = self.output_edit.text().strip()
        dup_raw = self.dup_edit.text().strip()

        if not in_raw:
            QtWidgets.QMessageBox.warning(self, "Invalid Input", "Input folder cannot be empty.")
            return
        if not out_raw:
            QtWidgets.QMessageBox.warning(self, "Invalid Output", "Output folder cannot be empty.")
            return
        if not dup_raw:
            QtWidgets.QMessageBox.warning(self, "Invalid Duplicates", "Duplicates folder cannot be empty.")
            return

        # 必须存在且是目录
        in_dir  = Path(in_raw)
        out_dir = Path(out_raw)
        dup_dir = Path(dup_raw)
        
        if not (in_dir.exists() and in_dir.is_dir()):
            QtWidgets.QMessageBox.warning(self, "Invalid Input", "Please select a valid input folder (must exist and be a directory).")
            return
        if not (out_dir.exists() and out_dir.is_dir()):
            QtWidgets.QMessageBox.warning(self, "Invalid Output", "Please select a valid output folder (must exist and be a directory).")
            return
        if not (dup_dir.exists() and dup_dir.is_dir()):
            QtWidgets.QMessageBox.warning(self, "Invalid Duplicates", "Please select a valid duplicates folder (must exist and be a directory).")
            return

        # UI 状态
        self.run_btn.setEnabled(False)
        #self.progress.setRange(0, 0)   # 不确定进度：转圈
        self.progress.setRange(0, 100)  # 初始化为 0-100
        self.progress.setValue(0)       # 进度归零
        self.progress.setFormat("%p%")  # 显示“xx%”
        self.status_label.setText("Running...")
        self.log_view.append("\n=== Start organizing ===\n")

        # 后台线程
        self.worker = OrganizeWorker(in_dir, out_dir, dup_dir, parent=self)

        self.worker.log.connect(self.append_log)
        self.worker.done.connect(self.on_done)
        self.worker.error.connect(self.on_error)

        self.worker.progress.connect(self.on_progress) # 绑定进度信号

        self.worker.finished.connect(self._on_worker_finished)
        self.worker.finished.connect(self.worker.deleteLater)

        self.worker.review_ready.connect(self.on_review_ready)

        self.worker.start()
    
    def _on_worker_finished(self):
        self.worker = None


    @QtCore.Slot(str)
    def append_log(self, text: str):
        self.log_view.moveCursor(QTextCursor.End)
        self.log_view.insertPlainText(text)
        self.log_view.moveCursor(QTextCursor.End)
    
    @QtCore.Slot(int)
    def on_progress(self, value: int):
        self.progress.setValue(value)

    @QtCore.Slot(int)
    def on_done(self, code: int):
        self.progress.setRange(0, 1)  # 停止旋转
        self.run_btn.setEnabled(True)
        if code == 0:
            self.status_label.setText("Completed")
            self.log_view.append("\n=== Completed ===")
        else:
            self.status_label.setText("Finished with errors")
            self.log_view.append("\n=== Finished with errors ===")
        #self.worker = None
    
    @QtCore.Slot(list)
    def on_review_ready(self, groups: list):
        # 处理完成后收到分组数据，弹出查看对话框
        self.last_groups = groups
        if groups:
            self.log_view.append(f"\n{len(groups)} duplicate groups detected."
                                 f"\nClick 'Review Duplicates' to inspect.")
            self.review_btn.setEnabled(True)  # 🆕 启用按钮
        else:
            self.log_view.append("\nNo duplicates found.")
            self.review_btn.setEnabled(False)

    def open_review(self):
        if not self.last_groups:
            QtWidgets.QMessageBox.information(self, "No Duplicates", "No duplicate groups were found.")
            return
        dlg = ReviewDialog(self.last_groups, self)
        dlg.exec()

    @QtCore.Slot(str)
    def on_error(self, msg: str):
        self.log_view.append(f"\n[ERROR] {msg}")

class ReviewDialog(QtWidgets.QDialog):
    def __init__(self, groups: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Duplicates Review")
        self.resize(1000, 680)
        self.groups = groups
        self.current_group_index = 0
        self.current_dupe_index = 0

        # 左侧：分组列表
        self.list_groups = QtWidgets.QListWidget()
        for g in self.groups:
            kind = g.get("kind", "?")
            keep = Path(g.get("keep", "")).name
            item = QtWidgets.QListWidgetItem(f"[{kind}] {keep}")
            self.list_groups.addItem(item)

        # 右侧：图片显示（保留图 vs 重复图）
        self.lbl_keep = QtWidgets.QLabel("KEEP")
        self.lbl_dupe = QtWidgets.QLabel("DUPE")
        for lbl in (self.lbl_keep, self.lbl_dupe):
            lbl.setAlignment(QtCore.Qt.AlignCenter)
            lbl.setMinimumSize(400, 300)
            lbl.setFrameShape(QtWidgets.QFrame.Box)
            lbl.setScaledContents(True)

        # 右侧控制区
        self.info_label = QtWidgets.QLabel("")
        self.btn_prev = QtWidgets.QPushButton("Prev dup")
        self.btn_next = QtWidgets.QPushButton("Next dup")
        self.btn_close = QtWidgets.QPushButton("Close")
        # 预留：未来可以加 “Promote this dupe as keep” 按钮

        ctrl = QtWidgets.QHBoxLayout()
        ctrl.addWidget(self.btn_prev)
        ctrl.addWidget(self.btn_next)
        ctrl.addStretch(1)
        ctrl.addWidget(self.btn_close)

        # —— 标题（新增）——
        self.title_keep = QtWidgets.QLabel("Main (kept)")
        self.title_dupe = QtWidgets.QLabel("Duplicate candidate")
        for t in (self.title_keep, self.title_dupe):
            t.setAlignment(QtCore.Qt.AlignCenter)
            font = t.font()
            font.setBold(True)
            t.setFont(font)

        # —— 左右两列（标题 + 图片）——
        left_col  = QtWidgets.QVBoxLayout()
        right_col = QtWidgets.QVBoxLayout()
        left_col.addWidget(self.title_keep)
        left_col.addWidget(self.lbl_keep, 1)
        right_col.addWidget(self.title_dupe)
        right_col.addWidget(self.lbl_dupe, 1)

        # —— 右侧整体布局 —— 
        right_layout = QtWidgets.QVBoxLayout()
        img_row = QtWidgets.QHBoxLayout()
        img_row.addLayout(left_col, 1)
        img_row.addLayout(right_col, 1)

        right_layout.addLayout(img_row)
        right_layout.addWidget(self.info_label)
        right_layout.addLayout(ctrl)

        # 总体布局
        main = QtWidgets.QHBoxLayout(self)
        main.addWidget(self.list_groups, 1)
        right_widget = QtWidgets.QWidget()
        right_widget.setLayout(right_layout)
        main.addWidget(right_widget, 3)

        # 信号
        self.list_groups.currentRowChanged.connect(self.on_group_changed)
        self.btn_prev.clicked.connect(self.prev_dupe)
        self.btn_next.clicked.connect(self.next_dupe)
        self.btn_close.clicked.connect(self.accept)

        # 初始化
        if self.groups:
            self.list_groups.setCurrentRow(0)

    def load_pix(self, path: str, target_label: QtWidgets.QLabel):
        p = Path(path)
        if p.exists():
            #pix = QtWidgets.QPixmap(str(p))
            pix = QPixmap(str(p))
            # 简单缩放适配
            target_label.setPixmap(pix)
        else:
            target_label.setText(f"Missing:\n{path}")

    def refresh_view(self):
        if not self.groups:
            return
        g = self.groups[self.current_group_index]
        keep_path = g.get("keep", "")
        dupes = g.get("dupes", []) or []
        # 保留图
        self.load_pix(keep_path, self.lbl_keep)
        # 当前重复图
        if dupes:
            di = max(0, min(self.current_dupe_index, len(dupes)-1))
            self.current_dupe_index = di
            self.load_pix(dupes[di], self.lbl_dupe)
            self.info_label.setText(f"Group {self.current_group_index+1}/{len(self.groups)}  •  Dupe {di+1}/{len(dupes)}")
        else:
            self.lbl_dupe.setText("No duplicates")
            self.info_label.setText(f"Group {self.current_group_index+1}/{len(self.groups)}  •  No dupes")

    def on_group_changed(self, row: int):
        if row < 0:
            return
        self.current_group_index = row
        self.current_dupe_index = 0
        self.refresh_view()

    def prev_dupe(self):
        if not self.groups:
            return
        g = self.groups[self.current_group_index]
        dupes = g.get("dupes", []) or []
        if not dupes:
            return
        self.current_dupe_index = (self.current_dupe_index - 1) % len(dupes)
        self.refresh_view()

    def next_dupe(self):
        if not self.groups:
            return
        g = self.groups[self.current_group_index]
        dupes = g.get("dupes", []) or []
        if not dupes:
            return
        self.current_dupe_index = (self.current_dupe_index + 1) % len(dupes)
        self.refresh_view()


def main():
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
