# LUMINA ANNOTATOR

A lightweight, multi-modal desktop annotation tool optimized for Computer Vision engineers and data scientists. 
Now powered by a modular MVC architecture!

## 🚀 Features
- **Multi-Modal**: Support for Images (BBox, Polygon, Point, Classification), Text (Spans), and CSV (Row Classification).
- **Fast, Minimalist UI**: Clean, light clinical theme designed for long annotation sessions. 
- **CV Engineer Ready**: Native export to standard ML formats like **YOLO** and **COCO**, as well as basic flattened CSVs/JSONs.
- **Session Persistence**: Save and reload your annotation progress using `.ann` files.
- **Extensive Logging**: Automatic logging to `lumina.log` tracks all session changes and file operations.

## 📦 Installation

To install the application globally so it can be run from anywhere:

```bash
# Clone the repository / navigate to the folder
cd annotator

# Install via pip
pip install -e .
```

## 🛠️ Usage

After installation, simply run:
```bash
lumina
```

### Advanced Qt Scale Demo
We have laid the groundwork for scaling the software via a Qt Graphics engine and AI integration directly in the workspace.

If you have downloaded the Ultralytics SAM dependencies and model weights (`FastSAM-s.pt`), you can launch the scaled architecture using:
```bash
python -m src.demo_advanced
```

## 🧠 Supported Annotation Types
### Images
* **BBox (Bounding Box):** `[Q]` Click and drag to create a bounding rectangle.
* **Polygon:** `[A]` Left-click to map points. Right-click to close and complete the polygon (perfect for segmentation).
* **Point:** `[W]` Pinpoint coordinates (perfect for pose estimation or keypoints).
* **Classify:** `[E]` Assign a label to the entire image.

### Text
* **Spans:** Highlight unstructured text and press your custom label shortcut to tag strings (NER).

### Tabular (CSV)
* **Row Classify:** Read data row-by-row and classify records. 
