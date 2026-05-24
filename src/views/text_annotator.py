from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTextEdit, QMessageBox
)
from PyQt6.QtGui import QTextCharFormat, QColor, QFont, QTextCursor
from PyQt6.QtCore import Qt
from ..config import LABEL_TEXT_FOR

class TextAnnotator(QWidget):
    def __init__(self, parent=None, on_new_annot=None, get_active_label=None):
        super().__init__(parent)
        self.on_new_annot = on_new_annot
        self.get_active_lbl = get_active_label
        self._annots = []
        self._text_content = ""
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel("<small>SELECT TEXT THEN CLICK TO ANNOTATE</small>"))
        info_layout.addStretch()
        
        btn_annot = QPushButton("ANNOTATE SELECTION")
        btn_annot.clicked.connect(self._annotate_selection)
        info_layout.addWidget(btn_annot)
        layout.addLayout(info_layout)
        
        self.txt = QTextEdit()
        self.txt.setReadOnly(True)
        self.txt.setFont(QFont("Courier", 10))
        layout.addWidget(self.txt)

    def load_text(self, content, annots):
        self._text_content = content
        self._annots = annots
        self.txt.setPlainText(content)
        self._apply_highlights()

    def refresh(self, annots):
        self._annots = annots
        self._apply_highlights()

    def _apply_highlights(self):
        # Reset formatting
        cursor = self.txt.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        fmt = QTextCharFormat()
        fmt.setBackground(QColor(Qt.GlobalColor.transparent))
        fmt.setForeground(QColor(Qt.GlobalColor.black)) # or adapt from theme
        cursor.setCharFormat(fmt)
        cursor.clearSelection()
        
        # Apply specific highlights
        for a in self._annots:
            if a["type"] != "span": continue
            shade = a.get("shade", "#888")
            start = a["data"]["start"]
            end = a["data"]["end"]
            
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            
            h_fmt = QTextCharFormat()
            h_fmt.setBackground(QColor(shade))
            txt_c = LABEL_TEXT_FOR.get(shade, "#ffffff")
            h_fmt.setForeground(QColor(txt_c))
            h_fmt.setFontWeight(QFont.Weight.Bold)
            cursor.setCharFormat(h_fmt)

    def _annotate_selection(self):
        lbl = self.get_active_lbl()
        if not lbl:
            QMessageBox.information(self, "No Label", "Select a label first.")
            return
            
        cursor = self.txt.textCursor()
        if not cursor.hasSelection():
            QMessageBox.information(self, "No Selection", "Select text first.")
            return
            
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        text = cursor.selectedText()
        
        if self.on_new_annot:
            self.on_new_annot({
                "type": "span", "label": lbl["name"],
                "shade": lbl["shade"],
                "data": {"start": start, "end": end, "text": text}
            })
        return offset
