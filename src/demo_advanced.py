from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QSlider, QComboBox, QFileDialog, QListWidget
)
from PyQt6.QtCore import Qt, QTimer
from src.views.q_image_canvas import LuminaImageCanvas
from src.logger import log
from src.sam_assistant import SamAssistant
import sys
import json
import cv2

class LuminaPyQtMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lumina Annotator (PyQt6 Advanced Scale)")
        self.resize(1200, 800)
        
        # Managers
        self.sam = SamAssistant()
        
        self.current_image_path = None
        self.cap = None
        self.is_playing = False
        self.total_frames = 0
        
        self.annotations = []
        self.active_label = {"name": "Object", "shade": "#FF5555"}
        
        # Video Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self._next_frame)
        
        self._init_ui()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Left Panel (Controls)
        left_panel = QVBoxLayout()
        main_layout.addLayout(left_panel, 1)
        
        # Drawing Modes
        left_panel.addWidget(QLabel("<b>Draw Mode</b>"))
        self.cb_mode = QComboBox()
        self.cb_mode.addItems(["PAN (Space)", "BBOX (Q)", "POLYGON (A)", "POINT (W)", "SAM (Magic Wand)"])
        self.cb_mode.currentTextChanged.connect(self._change_mode)
        left_panel.addWidget(self.cb_mode)
        
        # Image Adjustments (Brightness/Contrast)
        left_panel.addWidget(QLabel("<b>Brightness</b>"))
        self.sl_bright = QSlider(Qt.Orientation.Horizontal)
        self.sl_bright.setRange(10, 300) # 0.1x to 3.0x
        self.sl_bright.setValue(100)
        self.sl_bright.valueChanged.connect(self._update_adjustments)
        left_panel.addWidget(self.sl_bright)

        left_panel.addWidget(QLabel("<b>Contrast</b>"))
        self.sl_contrast = QSlider(Qt.Orientation.Horizontal)
        self.sl_contrast.setRange(10, 300)
        self.sl_contrast.setValue(100)
        self.sl_contrast.valueChanged.connect(self._update_adjustments)
        left_panel.addWidget(self.sl_contrast)
        
        # Load AI
        btn_load_ai = QPushButton("Load SAM Weights")
        btn_load_ai.clicked.connect(self._load_sam)
        left_panel.addWidget(btn_load_ai)
        
        left_panel.addStretch()

        # Center Panel (Canvas)
        center_panel = QVBoxLayout()
        main_layout.addLayout(center_panel, 4)
        
        # File IO
        top_bar = QHBoxLayout()
        btn_load = QPushButton("Load Image")
        btn_load.clicked.connect(self._load_image)
        top_bar.addWidget(btn_load)
        
        btn_load_vid = QPushButton("Load Video")
        btn_load_vid.clicked.connect(self._load_video)
        top_bar.addWidget(btn_load_vid)
        
        btn_export = QPushButton("Export JSON")
        btn_export.clicked.connect(self._export)
        top_bar.addWidget(btn_export)
        center_panel.addLayout(top_bar)
        
        # Advanced Graphics View
        self.canvas = LuminaImageCanvas()
        self.canvas.get_active_label = lambda: self.active_label
        self.canvas.on_annot_create = self._receive_annotation
        self.canvas.sam_inference_cb = self.sam.infer_point
        center_panel.addWidget(self.canvas)
        
        # Bottom Panel (Video Controls)
        video_bar = QHBoxLayout()
        self.btn_play = QPushButton("Play")
        self.btn_play.clicked.connect(self._toggle_play)
        video_bar.addWidget(self.btn_play)
        
        self.sl_timeline = QSlider(Qt.Orientation.Horizontal)
        self.sl_timeline.setEnabled(False)
        self.sl_timeline.sliderMoved.connect(self._seek_video) # Use sliderMoved to prevent jumpy scrubbing
        video_bar.addWidget(self.sl_timeline)
        
        self.lbl_frame = QLabel("0 / 0")
        video_bar.addWidget(self.lbl_frame)
        
        center_panel.addLayout(video_bar)

        # Right Panel (Annotations)
        right_panel = QVBoxLayout()
        main_layout.addLayout(right_panel, 1)
        right_panel.addWidget(QLabel("<b>Annotations</b>"))
        self.annot_list = QListWidget()
        right_panel.addWidget(self.annot_list)

    def _load_sam(self):
        log.info("Loading SAM model...")
        self.sam.load_model()
        if self.sam.loaded:
            log.info("SAM active!")

    def _change_mode(self, text):
        mode = text.split(" ")[0]
        self.canvas.set_mode(mode)

    def _update_adjustments(self):
        b = self.sl_bright.value() / 100.0
        c = self.sl_contrast.value() / 100.0
        self.canvas.set_adjustments(b, c)

    def _load_image(self):
        fp, _ = QFileDialog.getOpenFileName(self, "Select Image")
        if fp:
            self._cleanup_video()
            self.current_image_path = fp
            self.annotations = []
            self.annot_list.clear() # Clear specific lists
            self.canvas.load_image(fp)

    def _load_video(self):
        fp, _ = QFileDialog.getOpenFileName(self, "Select Video", "", "Videos (*.mp4 *.mov *.avi)")
        if fp:
            self._cleanup_video()
            self.cap = cv2.VideoCapture(fp)
            if self.cap.isOpened():
                self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self.sl_timeline.setEnabled(True)
                self.sl_timeline.setRange(0, self.total_frames - 1)
                self.sl_timeline.setValue(0)
                fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
                self.timer.setInterval(int(1000 / fps))
                self._next_frame() # Read frame 0
                log.info(f"Loaded video: {fp} with {self.total_frames} frames")
            else:
                log.error("Failed to read video")

    def _cleanup_video(self):
        self.timer.stop()
        self.is_playing = False
        self.btn_play.setText("Play")
        if self.cap:
            self.cap.release()
            self.cap = None

    def _toggle_play(self):
        if not self.cap: return
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.timer.start()
            self.btn_play.setText("Pause")
        else:
            self.timer.stop()
            self.btn_play.setText("Play")

    def _seek_video(self, position):
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, position)
            self._next_frame()

    def _next_frame(self):
        if not self.cap: return
        ret, frame = self.cap.read()
        if ret:
            self.canvas.set_cv_image(frame)
            current_idx = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
            # Block signals temporarily if setting value while playing
            self.sl_timeline.blockSignals(True)
            self.sl_timeline.setValue(current_idx)
            self.sl_timeline.blockSignals(False)
            self.lbl_frame.setText(f"{current_idx} / {self.total_frames}")
        else:
            self._toggle_play() # Pause at end

    def _receive_annotation(self, annot):
        self.annotations.append(annot)
        self.annot_list.addItem(f"{annot['type'].upper()} ({annot['label']})")
        self.canvas.redraw_annotations(self.annotations)
        self.canvas.set_mode("PAN")
        self.cb_mode.setCurrentIndex(0)

    def _export(self):
        with open("export.json", "w") as f:
            json.dump(self.annotations, f, indent=2)
        log.info("Exported annotations to export.json")

def start_pyqt_app():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = LuminaPyQtMainWindow()
    win.show()
    sys.exit(app.exec())
