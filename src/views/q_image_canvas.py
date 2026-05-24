from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsPolygonItem, QGraphicsEllipseItem, QMessageBox
from PyQt6.QtGui import QPixmap, QImage, QColor, QPen, QBrush, QPolygonF
from PyQt6.QtCore import Qt, QRectF, QPointF
from PIL import Image, ImageEnhance
import cv2
import numpy as np

# A complete PyQt6 QGraphicsView implementing Zoom, Pan, Brightness, and BBox/Polygon drawing
class LuminaImageCanvas(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHints(self.renderHints() | Qt.RenderHint.Antialiasing | Qt.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag) # Built in panning!
        
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)
        
        # State
        self.current_cv_image = None
        self.current_pil_image = None
        self.draw_mode = "PAN" # PAN, BBOX, POINT, POLYGON, SAM
        self.zoom_factor = 1.15
        
        # Drawing Tracking
        self.start_pos = None
        self.temp_rect = None
        self.poly_points = []
        self.temp_lines = []
        
        # Callbacks
        self.on_annot_create = None
        self.get_active_label = None
        self.sam_inference_cb = None

        # Image Adjustments
        self.brightness = 1.0
        self.contrast = 1.0

    def load_image(self, fp):
        self.current_cv_image = cv2.imdecode(np.fromfile(fp, dtype=np.uint8), cv2.IMREAD_COLOR)
        if self.current_cv_image is not None:
            self.current_cv_image = cv2.cvtColor(self.current_cv_image, cv2.COLOR_BGR2RGB)
            self.current_pil_image = Image.fromarray(self.current_cv_image)
            self._apply_adjustments_and_render()
            self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def set_cv_image(self, cv_img):
        """Allows direct injection of a frame from a VideoCapture source"""
        if cv_img is not None:
            self.current_cv_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
            self.current_pil_image = Image.fromarray(self.current_cv_image)
            self._apply_adjustments_and_render()

    def _apply_adjustments_and_render(self):
        if self.current_pil_image is None: return
        img = self.current_pil_image
        
        if self.brightness != 1.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(self.brightness)
        if self.contrast != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(self.contrast)

        img_np = np.array(img)
        h, w, ch = img_np.shape
        bytes_per_line = ch * w
        qimg = QImage(img_np.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self.pixmap_item.setPixmap(QPixmap.fromImage(qimg))
        self.scene.setSceneRect(QRectF(self.pixmap_item.pixmap().rect()))

    def set_adjustments(self, brightness, contrast):
        self.brightness = brightness
        self.contrast = contrast
        self._apply_adjustments_and_render()

    def set_mode(self, mode):
        self.draw_mode = mode
        if mode == "PAN":
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        elif mode == "SAM":
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.setCursor(Qt.CursorShape.CrossCursor)
        
        # Clear temp geometries
        if self.temp_rect:
            self.scene.removeItem(self.temp_rect)
            self.temp_rect = None
        for line in self.temp_lines:
            self.scene.removeItem(line)
        self.temp_lines = []
        self.poly_points = []
            
    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.scale(self.zoom_factor, self.zoom_factor)
        else:
            self.scale(1.0 / self.zoom_factor, 1.0 / self.zoom_factor)

    def mousePressEvent(self, event):
        if self.draw_mode == "PAN" or event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
            
        scene_pos = self.mapToScene(event.pos())
        self.start_pos = scene_pos
        
        lbl = self.get_active_label() if self.get_active_label else {"name": "Default", "shade": "#FF0000"}
        pen = QPen(QColor(lbl["shade"]), 2)
        
        if self.draw_mode == "BBOX":
            self.temp_rect = QGraphicsRectItem(QRectF(scene_pos, scene_pos))
            self.temp_rect.setPen(pen)
            self.scene.addItem(self.temp_rect)
            
        elif self.draw_mode == "POLYGON":
            self.poly_points.append(scene_pos)
            if len(self.poly_points) > 1:
                p1 = self.poly_points[-2]
                p2 = self.poly_points[-1]
                line = self.scene.addLine(p1.x(), p1.y(), p2.x(), p2.y(), pen)
                self.temp_lines.append(line)
                
        elif self.draw_mode == "POINT":
            if self.on_annot_create:
                self.on_annot_create({
                    "type": "point", "label": lbl["name"], "shade": lbl["shade"],
                    "data": {"x": scene_pos.x(), "y": scene_pos.y()}
                })
                
        elif self.draw_mode == "SAM":
             # Invoke the SAM fast inference using the point!
             if self.sam_inference_cb:
                 poly_dict = self.sam_inference_cb(self.current_cv_image, int(scene_pos.x()), int(scene_pos.y()))
                 if poly_dict and self.on_annot_create:
                     poly_dict["label"] = lbl["name"]
                     poly_dict["shade"] = lbl["shade"]
                     self.on_annot_create(poly_dict)

    def mouseMoveEvent(self, event):
        if self.draw_mode == "PAN":
            super().mouseMoveEvent(event)
            return
            
        if self.draw_mode == "BBOX" and self.temp_rect and self.start_pos:
            scene_pos = self.mapToScene(event.pos())
            rect = QRectF(self.start_pos, scene_pos).normalized()
            self.temp_rect.setRect(rect)

    def mouseReleaseEvent(self, event):
        if self.draw_mode == "PAN":
            super().mouseReleaseEvent(event)
            return

        lbl = self.get_active_label() if self.get_active_label else {"name": "Default", "shade": "#FF0000"}
        
        if self.draw_mode == "BBOX" and self.temp_rect:
            rect = self.temp_rect.rect()
            if rect.width() > 5 and rect.height() > 5 and self.on_annot_create:
                self.on_annot_create({
                    "type": "bbox", "label": lbl["name"], "shade": lbl["shade"],
                    "data": {"x1": rect.left(), "y1": rect.top(), "x2": rect.right(), "y2": rect.bottom()}
                })
            self.scene.removeItem(self.temp_rect)
            self.temp_rect = None

        elif self.draw_mode == "POLYGON" and event.button() == Qt.MouseButton.RightButton:
            # Complete the polygon
            if len(self.poly_points) > 2 and self.on_annot_create:
                pts = [[p.x(), p.y()] for p in self.poly_points]
                self.on_annot_create({
                    "type": "polygon", "label": lbl["name"], "shade": lbl["shade"],
                    "data": {"points": pts}
                })
            self.set_mode("POLYGON") # resets the temp arrays

    def redraw_annotations(self, annots):
        # Clear specific drawn items
        for item in self.scene.items():
            if item != self.pixmap_item:
                self.scene.removeItem(item)
                
        for a in annots:
            lbl, shade, d = a.get("label", "?"), a.get("shade", "#ff0000"), a.get("data", {})
            pen = QPen(QColor(shade), 2)
            brush = QBrush(QColor(shade))
            
            if a["type"] == "bbox":
                rect = QRectF(d["x1"], d["y1"], d["x2"]-d["x1"], d["y2"]-d["y1"])
                self.scene.addRect(rect, pen)
                # Text label drawing omitted for brevity
            elif a["type"] == "polygon":
                qpoly = QPolygonF([QPointF(pt[0], pt[1]) for pt in d["points"]])
                # Draw polygon with transparent fill
                poly_brush = QBrush(QColor(shade))
                color = poly_brush.color()
                color.setAlpha(60)
                poly_brush.setColor(color)
                self.scene.addPolygon(qpoly, pen, poly_brush)
            elif a["type"] == "point":
                self.scene.addEllipse(d["x"]-4, d["y"]-4, 8, 8, pen, brush)
