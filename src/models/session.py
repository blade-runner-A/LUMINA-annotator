import json, csv, datetime, os
from collections import defaultdict
from ..logger import log

class AnnotationSession:
    """Holds all annotations for a loaded dataset."""

    def __init__(self):
        self.mode      = None   # "image" | "text" | "csv"
        self.items     = []     # list of file paths or row dicts
        self.annots    = {}     # {item_id: [annot, ...]}
        # annot = {"type": "bbox"|"point"|"polygon"|"classify"|"span"|"row",
        #          "label": str, "data": {...}}

    def set_annot(self, item_id, annot_list):
        self.annots[item_id] = annot_list

    def get_annot(self, item_id):
        return self.annots.get(item_id, [])

    def add_annot(self, item_id, annot):
        self.annots.setdefault(item_id, []).append(annot)
        log.debug(f"Added annotation {annot['type'].upper()} for item {item_id}")

    def remove_annot(self, item_id, idx):
        lst = self.annots.get(item_id, [])
        if 0 <= idx < len(lst):
            lst.pop(idx)
            log.debug(f"Removed annotation at idx {idx} for item {item_id}")

    def export_yolo(self, dir_path, label_store):
        """Export BBox annotations in YOLO format (.txt files)."""
        os.makedirs(dir_path, exist_ok=True)
        labels_obj = label_store.labels
        label_to_idx = {lb["name"]: i for i, lb in enumerate(labels_obj)}
        
        # Write classes.txt
        with open(os.path.join(dir_path, "classes.txt"), "w") as f:
            for lb in labels_obj: 
                f.write(lb["name"] + "\n")
                
        # We need image dimensions to normalize coordinates.
        try:
            from PIL import Image
        except ImportError:
            log.error("PIL is required for YOLO export dimensions.")
            return

        exported = 0
        for i, item in enumerate(self.items):
            annots = self.get_annot(str(i))
            if not annots: continue
            
            try:
                with Image.open(item) as img:
                    w, h = img.size
            except Exception as e:
                log.error(f"Could not read image {item} for YOLO export: {e}")
                continue
            
            base = os.path.splitext(os.path.basename(item))[0]
            txt_path = os.path.join(dir_path, f"{base}.txt")
            
            with open(txt_path, "w") as f:
                for a in annots:
                    if a["type"] == "bbox":
                        d = a["data"]
                        cls_id = label_to_idx.get(a["label"], 0)
                        cx = ((d["x1"] + d["x2"]) / 2.0) / w
                        cy = ((d["y1"] + d["y2"]) / 2.0) / h
                        bw = abs(d["x2"] - d["x1"]) / w
                        bh = abs(d["y2"] - d["y1"]) / h
                        f.write(f"{cls_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n")
            exported += 1
        log.info(f"YOLO export complete: {exported} files written to {dir_path}")

    def export_coco(self, path, label_store):
        """Export generic COCO formatted dictionary for BBox/Polygons."""
        labels_obj = label_store.labels
        categories = [{"id": i, "name": lb["name"]} for i, lb in enumerate(labels_obj)]
        label_to_cat = {lb["name"]: i for i, lb in enumerate(labels_obj)}
        
        coco = {
            "info": {"description": "Spectra Annotator Export", "date_created": datetime.datetime.now().isoformat()},
            "images": [],
            "annotations": [],
            "categories": categories
        }
        
        try:
            from PIL import Image
        except ImportError:
            log.error("PIL is required for COCO export.")
            return

        annot_id = 0
        for i, item in enumerate(self.items):
            try:
                with Image.open(item) as img:
                    w, h = img.size
            except Exception:
                continue
                
            img_id = i
            coco["images"].append({
                "id": img_id,
                "file_name": os.path.basename(item),
                "width": w,
                "height": h
            })
            
            annots = self.get_annot(str(i))
            for a in annots:
                d = a["data"]
                cat_id = label_to_cat.get(a["label"], 0)
                
                if a["type"] == "bbox":
                    bw = abs(d["x2"] - d["x1"])
                    bh = abs(d["y2"] - d["y1"])
                    coco["annotations"].append({
                        "id": annot_id,
                        "image_id": img_id,
                        "category_id": cat_id,
                        "bbox": [min(d["x1"], d["x2"]), min(d["y1"], d["y2"]), bw, bh],
                        "area": bw * bh,
                        "iscrowd": 0
                    })
                    annot_id += 1
                elif a["type"] == "polygon":
                    pts = d["points"] # [[x,y], [x,y]]
                    flat_pts = [c for pt in pts for c in pt]
                    xs = [pt[0] for pt in pts]
                    ys = [pt[1] for pt in pts]
                    xmin, xmax = min(xs), max(xs)
                    ymin, ymax = min(ys), max(ys)
                    coco["annotations"].append({
                        "id": annot_id,
                        "image_id": img_id,
                        "category_id": cat_id,
                        "segmentation": [flat_pts],
                        "bbox": [xmin, ymin, xmax - xmin, ymax - ymin],
                        "area": (xmax - xmin) * (ymax - ymin), # naive box area
                        "iscrowd": 0
                    })
                    annot_id += 1

        with open(path, "w") as f:
            json.dump(coco, f, indent=2)
        log.info(f"COCO export complete: saved to {path} with {annot_id} annotations")

    def export_json(self, path):
        out = {
            "meta": {
                "tool":    "LUMINA ANNOTATOR",
                "exported": datetime.datetime.now().isoformat(),
                "mode":    self.mode,
                "items":   len(self.items),
            },
            "annotations": {}
        }
        for k, v in self.annots.items():
            out["annotations"][str(k)] = v
        with open(path, "w") as f:
            json.dump(out, f, indent=2)

    def export_csv_flat(self, path):
        rows = []
        for item_id, annots in self.annots.items():
            for a in annots:
                rows.append({
                    "item_id": item_id,
                    "type":    a.get("type",""),
                    "label":   a.get("label",""),
                    "data":    json.dumps(a.get("data",{})),
                })
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["item_id","type","label","data"])
            w.writeheader()
            w.writerows(rows)

    def to_dict(self):
        return {
            "mode":    self.mode,
            "items":   self.items,
            "annots":  {str(k):v for k,v in self.annots.items()},
        }

    def from_dict(self, d):
        self.mode  = d.get("mode")
        self.items = d.get("items", [])
        self.annots= {k:v for k,v in d.get("annots",{}).items()}
