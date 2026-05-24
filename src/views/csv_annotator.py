from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QScrollArea, QFrame, QFormLayout
)
from PyQt6.QtCore import Qt
from ..config import LABEL_TEXT_FOR

class CSVAnnotator(QWidget):
    def __init__(self, parent=None, on_new_annot=None, get_active_label=None):
        super().__init__(parent)
        self.on_new_annot = on_new_annot
        self.get_active_lbl = get_active_label
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        info = QLabel("<small>ROW DATA — Select a label or press its key shortcut to classify</small>")
        layout.addWidget(info)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        layout.addWidget(self.scroll)
        
        self.inner_widget = QWidget()
        self.inner_layout = QVBoxLayout(self.inner_widget)
        self.inner_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.inner_widget)

    def load_row(self, row_dict, annots):
        # Clear inner layout
        while self.inner_layout.count():
            item = self.inner_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.inner_layout.addWidget(QLabel("<b>FIELDS</b>"))
        
        form_layout = QFormLayout()
        for k, v in row_dict.items():
            val_lbl = QLabel(str(v)[:300])
            val_lbl.setWordWrap(True)
            form_layout.addRow(QLabel(f"<small><b>{str(k).upper()}</b></small>"), val_lbl)
        
        container = QWidget()
        container.setLayout(form_layout)
        container.setStyleSheet("background-color: #2b2b2b; padding: 8px; border-radius: 4px;") # Basic styling
        self.inner_layout.addWidget(container)

        # Show existing annotations for this row
        if annots:
            self.inner_layout.addSpacing(16)
            self.inner_layout.addWidget(QLabel("<b>CURRENT ANNOTATIONS</b>"))
            
            for a in annots:
                shade = a.get("shade", "#888")
                txt_c = LABEL_TEXT_FOR.get(shade, "#ffffff")
                lbl = QLabel(f" {a['label']} ")
                lbl.setStyleSheet(f"background-color: {shade}; color: {txt_c}; font-weight: bold; padding: 4px;")
                self.inner_layout.addWidget(lbl)

    def refresh(self, annots):
        pass  # handled by parent reloading
