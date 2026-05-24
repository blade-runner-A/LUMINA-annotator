from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QWidget, QMessageBox
)
from PyQt6.QtCore import Qt
from ..config import LABEL_SHADES

class LabelDialog(QDialog):
    def __init__(self, parent=None, existing=None):
        super().__init__(parent)
        self.setWindowTitle("Label")
        self.resize(320, 220)
        self.result = None
        
        ex = existing or {}
        self.name_val = ex.get("name", "")
        self.key_val = ex.get("key", "")
        self.shade_val = ex.get("shade", LABEL_SHADES[0])
        
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<b>LABEL NAME</b><br/><small>e.g. 'Cat', 'Positive', 'Entity'</small>"))
        self.name_edit = QLineEdit(self.name_val)
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("<b>KEYBOARD SHORTCUT</b><br/><small>Single character, e.g. c / 1 / a</small>"))
        self.key_edit = QLineEdit(self.key_val)
        layout.addWidget(self.key_edit)

        layout.addWidget(QLabel("<b>COLOUR SHADE</b>"))
        shade_layout = QHBoxLayout()
        self._shade_btns = []
        for s in LABEL_SHADES:
            btn = QPushButton()
            btn.setFixedSize(24, 24)
            btn.setStyleSheet(f"background-color: {s}; border: none;")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, _s=s: self._pick_shade(_s))
            shade_layout.addWidget(btn)
            self._shade_btns.append((s, btn))
        shade_layout.addStretch()
        layout.addLayout(shade_layout)
        
        self._pick_shade(self.shade_val)

        bot_layout = QHBoxLayout()
        bot_layout.addStretch()
        
        btn_cancel = QPushButton("CANCEL")
        btn_cancel.clicked.connect(self.reject)
        bot_layout.addWidget(btn_cancel)
        
        btn_apply = QPushButton("APPLY")
        btn_apply.clicked.connect(self._apply)
        btn_apply.setDefault(True)
        bot_layout.addWidget(btn_apply)
        
        layout.addLayout(bot_layout)

    def _pick_shade(self, shade):
        self.shade_val = shade
        for s, btn in self._shade_btns:
            border = "border: 2px solid white;" if s == shade else "border: none;"
            btn.setStyleSheet(f"background-color: {s}; {border}")

    def _apply(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Label", "Name is required.")
            return
            
        self.result = {
            "name": name,
            "key": self.key_edit.text().strip()[:1],
            "shade": self.shade_val,
        }
        self.accept()
