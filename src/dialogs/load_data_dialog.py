from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFileDialog, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt
from pathlib import Path
import re, csv

class LoadDataDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Load Data")
        self.resize(440, 340)
        self.result = None
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        
        title = QLabel("<b>LOAD DATA</b>")
        layout.addWidget(title)

        options = [
            ("🖼", "IMAGE FOLDER", "Load a folder of images (JPG, PNG).\nFor bounding-box/polygon annotations.", self._load_images),
            ("📄", "TEXT FILE", "Load a plain-text or JSON-lines file.\nAnnotate spans, classify lines.", self._load_text),
            ("📊", "CSV / TSV FILE", "Load tabular data. Annotate each row.", self._load_csv),
        ]

        for icon, hdr, desc, cmd in options:
            btn = QPushButton()
            # We can use a custom layout inside the button or a custom widget for the neat layout
            row_layout = QHBoxLayout()
            row_layout.addWidget(QLabel(f"<span style='font-size:24px;'>{icon}</span>"))
            
            text_layout = QVBoxLayout()
            text_layout.addWidget(QLabel(f"<b>{hdr}</b>"))
            text_layout.addWidget(QLabel(f"<small>{desc}</small>"))
            row_layout.addLayout(text_layout)
            row_layout.addStretch()
            row_layout.addWidget(QLabel("→"))
            
            btn.setLayout(row_layout)
            btn.clicked.connect(cmd)
            layout.addWidget(btn)

        bot_layout = QHBoxLayout()
        bot_layout.addStretch()
        btn_cancel = QPushButton("CANCEL")
        btn_cancel.clicked.connect(self.reject)
        bot_layout.addWidget(btn_cancel)
        layout.addLayout(bot_layout)

    def _load_images(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if not folder: return
        exts = {".jpg",".jpeg",".png",".bmp",".webp",".gif",".tiff"}
        items = sorted([str(p) for p in Path(folder).iterdir() if p.suffix.lower() in exts])
        if not items:
            QMessageBox.information(self, "No Images", "No supported images found in folder.")
            return
        self.result = ("image", items)
        self.accept()

    def _load_text(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Text File", "", "Text/JSONL (*.txt *.jsonl);;All (*.*)")
        if not path: return
        with open(path, encoding="utf-8", errors="replace") as fi:
            raw = fi.read()
        if path.endswith(".jsonl"):
            items = [line.strip() for line in raw.splitlines() if line.strip()]
        else:
            items = [p.strip() for p in re.split(r"\n{2,}", raw) if p.strip()]
        if not items:
            items = [raw]
        self.result = ("text", items)
        self.accept()

    def _load_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select CSV / TSV File", "", "CSV/TSV (*.csv *.tsv);;All (*.*)")
        if not path: return
        delim = "\t" if path.endswith(".tsv") else ","
        items = []
        with open(path, encoding="utf-8", errors="replace", newline="") as fi:
            reader = csv.DictReader(fi, delimiter=delim)
            for row in reader:
                items.append(dict(row))
        if not items:
            QMessageBox.information(self, "Empty", "No rows found.")
            return
        self.result = ("csv", items)
        self.accept()
