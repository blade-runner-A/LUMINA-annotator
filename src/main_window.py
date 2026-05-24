import tkinter as tk
from tkinter import filedialog, messagebox
import os, json

from .config import U, LABEL_SHADES, LABEL_TEXT_FOR
from .ui_helpers import _btn, _label, _sep, _entry
from .logger import log
from .models.label_store import LabelStore
from .models.session import AnnotationSession
from .dialogs.label_dialog import LabelDialog
from .dialogs.load_data_dialog import LoadDataDialog
from .views.image_canvas import ImageCanvas
from .views.text_annotator import TextAnnotator
from .views.csv_annotator import CSVAnnotator

class LuminaAnnotator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LUMINA ANNOTATOR")
        self.configure(bg=U["bg"])
        self.geometry("1200x780")
        self.minsize(900, 600)
        log.info("Initialized LuminaAnnotator Window")

        self.label_store = LabelStore()
        self.session     = AnnotationSession()
        self.cur_idx     = 0
        self._active_lbl = None   # currently selected label dict

        self._build_ui()
        self._load_demo()
        self.bind("<Key>", self._on_key)

    # ── BUILD ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── top bar ──────────────────────────────────────────────────────────
        top = tk.Frame(self, bg=U["surface"], height=44)
        top.pack(fill="x")
        top.pack_propagate(False)

        tk.Label(top, text="LUMINA", bg=U["surface"], fg=U["text"],
                 font=("Courier",13,"bold")).pack(side="left",padx=14)
        tk.Label(top, text="ANNOTATOR", bg=U["surface"], fg=U["text3"],
                 font=("Courier",9)).pack(side="left")

        for lbl, cmd, ac in [
            ("COCO",          self._export_coco,  False),
            ("YOLO",          self._export_yolo,  False),
            ("CSV",           self._export_csv,   False),
            ("SAVE SESSION",  self._save_session, False),
            ("LOAD SESSION",  self._load_session, False),
            ("LOAD DATA",     self._load_data,    True),
        ]:
            _btn(top, lbl, cmd, accent=ac).pack(side="right", padx=(0,6))

        _sep(self).pack(fill="x")

        # ── body ─────────────────────────────────────────────────────────────
        body = tk.Frame(self, bg=U["bg"])
        body.pack(fill="both", expand=True)

        # LEFT
        left = tk.Frame(body, bg=U["surface"], width=210)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        self._build_left(left)
        _sep(body, vertical=True).pack(side="left", fill="y")

        # CENTER
        center = tk.Frame(body, bg=U["bg"])
        center.pack(side="left", fill="both", expand=True)
        self._build_center(center)

        _sep(body, vertical=True).pack(side="left", fill="y")

        # RIGHT
        right = tk.Frame(body, bg=U["surface"], width=230)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)
        self._build_right(right)

        # ── status bar ───────────────────────────────────────────────────────
        sbar = tk.Frame(self, bg=U["surface2"], height=24)
        sbar.pack(fill="x", side="bottom")
        sbar.pack_propagate(False)
        self.status_var = tk.StringVar(value="Ready — load data to begin.")
        tk.Label(sbar, textvariable=self.status_var,
                 bg=U["surface2"], fg=U["text3"],
                 font=("Courier",7), anchor="w",
                 padx=12).pack(fill="x")

    # ── LEFT PANEL ───────────────────────────────────────────────────────────

    def _build_left(self, parent):
        # Section: LABELS
        lf = tk.Frame(parent, bg=U["surface"], padx=10, pady=8)
        lf.pack(fill="x")

        hdr = tk.Frame(lf, bg=U["surface"])
        hdr.pack(fill="x")
        _label(hdr, "LABELS", bold=True, size=7).pack(side="left")
        _btn(hdr, "+ ADD", self._add_label, small=True, padx=6, pady=2
             ).pack(side="right")

        _sep(lf, color=U["border2"]).pack(fill="x", pady=(4,6))

        self.label_frame = tk.Frame(lf, bg=U["surface"])
        self.label_frame.pack(fill="x")

        _sep(parent).pack(fill="x")

        # Section: PROGRESS
        pf = tk.Frame(parent, bg=U["surface"], padx=10, pady=8)
        pf.pack(fill="x")
        _label(pf, "PROGRESS", bold=True, size=7).pack(anchor="w")
        _sep(pf, color=U["border2"]).pack(fill="x", pady=(4,6))

        self.progress_var = tk.StringVar(value="— / —")
        tk.Label(pf, textvariable=self.progress_var,
                 bg=U["surface"], fg=U["text"],
                 font=("Courier",20,"bold")).pack(anchor="w")

        self.prog_canvas = tk.Canvas(pf, bg=U["surface3"], height=6,
                                      highlightthickness=0)
        self.prog_canvas.pack(fill="x", pady=(4,0))

        _sep(parent).pack(fill="x")

        # Section: NAVIGATE
        nf = tk.Frame(parent, bg=U["surface"], padx=10, pady=8)
        nf.pack(fill="x")
        _label(nf, "NAVIGATE", bold=True, size=7).pack(anchor="w")
        _sep(nf, color=U["border2"]).pack(fill="x", pady=(4,6))

        nav = tk.Frame(nf, bg=U["surface"])
        nav.pack(fill="x")
        _btn(nav, "← PREV", self._go_prev).pack(side="left", fill="x", expand=True, padx=(0,3))
        _btn(nav, "NEXT →", self._go_next).pack(side="left", fill="x", expand=True, padx=(3,0))

        _sep(parent).pack(fill="x", pady=(4,0))

        # jump
        jf = tk.Frame(parent, bg=U["surface"], padx=10, pady=6)
        jf.pack(fill="x")
        _label(jf, "JUMP TO #", size=6).pack(anchor="w")
        self.jump_var = tk.StringVar()
        je = _entry(jf, self.jump_var)
        je.pack(fill="x", pady=(2,0), ipady=4)
        je.bind("<Return>", self._jump)

    # ── CENTER PANEL ─────────────────────────────────────────────────────────

    def _build_center(self, parent):
        # item title bar
        title_bar = tk.Frame(parent, bg=U["surface2"], height=30)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)

        self.item_title_var = tk.StringVar(value="No data loaded")
        tk.Label(title_bar, textvariable=self.item_title_var,
                 bg=U["surface2"], fg=U["text2"],
                 font=("Courier",8), anchor="w",
                 padx=10).pack(fill="both", expand=True)

        _sep(parent).pack(fill="x")

        # notebook-like tab row
        tabs = tk.Frame(parent, bg=U["surface"])
        tabs.pack(fill="x")
        self._mode_var = tk.StringVar(value="image")
        for m, lbl in [("image","IMAGE"),("text","TEXT"),("csv","CSV / TABLE")]:
            rb = tk.Radiobutton(tabs, text=lbl, variable=self._mode_var, value=m,
                                bg=U["surface"], fg=U["text3"],
                                selectcolor=U["surface3"],
                                activebackground=U["surface"],
                                font=("Courier",8,"bold"),
                                relief="flat", indicatoron=False,
                                padx=14, pady=6,
                                highlightthickness=0,
                                command=self._on_mode_change)
            rb.pack(side="left", padx=2, pady=4)

        _sep(parent).pack(fill="x")

        # content area — stacked frames, show/hide
        self.content_area = tk.Frame(parent, bg=U["bg"])
        self.content_area.pack(fill="both", expand=True)

        self.img_annotator = ImageCanvas(
            self.content_area,
            on_new_annot   = self._on_new_annot,
            get_active_label=self._get_active_label)

        self.txt_annotator = TextAnnotator(
            self.content_area,
            on_new_annot   = self._on_new_annot,
            get_active_label=self._get_active_label)

        self.csv_annotator = CSVAnnotator(
            self.content_area,
            on_new_annot   = self._on_new_annot,
            get_active_label=self._get_active_label)

        self._show_panel("image")

    # ── RIGHT PANEL ──────────────────────────────────────────────────────────

    def _build_right(self, parent):
        hdr = tk.Frame(parent, bg=U["surface"], padx=10, pady=8)
        hdr.pack(fill="x")
        hdr_row = tk.Frame(hdr, bg=U["surface"])
        hdr_row.pack(fill="x")
        _label(hdr_row, "ANNOTATIONS", bold=True, size=7).pack(side="left")
        _btn(hdr_row, "✕ CLEAR ALL", self._clear_all_annots,
             small=True, padx=6, pady=2).pack(side="right")

        _sep(parent).pack(fill="x")

        # annotation list
        list_frame = tk.Frame(parent, bg=U["bg"])
        list_frame.pack(fill="both", expand=True)
        sb = tk.Scrollbar(list_frame, orient="vertical",
                          bg=U["surface"], troughcolor=U["bg"])
        self.annot_listbox = tk.Listbox(
            list_frame,
            bg=U["bg"], fg=U["text2"],
            selectbackground=U["surface3"],
            selectforeground=U["text"],
            font=("Courier",8),
            relief="flat", bd=0,
            highlightthickness=0,
            activestyle="none",
            yscrollcommand=sb.set)
        sb.config(command=self.annot_listbox.yview)
        sb.pack(side="right", fill="y")
        self.annot_listbox.pack(side="left", fill="both", expand=True)

        _sep(parent).pack(fill="x")

        bot = tk.Frame(parent, bg=U["surface"], padx=10, pady=6)
        bot.pack(fill="x", side="bottom")
        _btn(bot, "✕ REMOVE SELECTED",
             self._remove_selected_annot,
             small=True).pack(fill="x")

        _sep(parent).pack(fill="x", side="bottom")
        self.annot_count_var = tk.StringVar(value="0 annotations")
        tk.Label(parent,
                 textvariable=self.annot_count_var,
                 bg=U["surface"], fg=U["text3"],
                 font=("Courier",7),
                 anchor="w", padx=10).pack(fill="x", side="bottom", pady=3)

    # ── LABEL UI ─────────────────────────────────────────────────────────────

    def _refresh_labels(self):
        for w in self.label_frame.winfo_children():
            w.destroy()

        for i, lb in enumerate(self.label_store.labels):
            rf = tk.Frame(self.label_frame, bg=U["surface"])
            rf.pack(fill="x", pady=2)
            is_active = (self._active_lbl and
                         self._active_lbl["name"] == lb["name"])
            shade = lb["shade"]
            txt_c = LABEL_TEXT_FOR.get(shade,"#eee")
            indicator_bg = shade if is_active else U["surface3"]
            indicator_fg = txt_c if is_active else U["text2"]
            key_str = f"[{lb['key']}]" if lb["key"] else ""

            btn = tk.Button(rf,
                text=f"  {lb['name']}  {key_str}",
                command=lambda _lb=lb: self._select_label(_lb),
                bg=indicator_bg, fg=indicator_fg,
                relief="flat",
                font=("Courier",8,"bold" if is_active else "normal"),
                anchor="w",
                padx=4, pady=4,
                activebackground=shade,
                activeforeground=txt_c,
                cursor="hand2")
            btn.pack(side="left", fill="x", expand=True)

            # edit/delete
            for sym, cmd in [("✎", lambda _i=i: self._edit_label(_i)),
                              ("✕", lambda _i=i: self._del_label(_i))]:
                tk.Button(rf, text=sym, command=cmd,
                          bg=U["surface"], fg=U["text3"],
                          relief="flat",
                          font=("Courier",8),
                          padx=3, pady=4,
                          activebackground=U["border2"],
                          cursor="hand2").pack(side="right")

    def _add_label(self):
        dlg = LabelDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            self.label_store.add(**dlg.result)
            self._refresh_labels()

    def _edit_label(self, idx):
        lb = self.label_store.get(idx)
        if not lb: return
        dlg = LabelDialog(self, existing=lb)
        self.wait_window(dlg)
        if dlg.result:
            self.label_store._labels[idx] = dlg.result
            self._refresh_labels()

    def _del_label(self, idx):
        self.label_store.remove(idx)
        self._active_lbl = None
        self._refresh_labels()

    def _select_label(self, lb):
        self._active_lbl = lb
        self._refresh_labels()
        self._set_status(f"Active label: {lb['name']}  [{lb.get('key','')}]")

    def _get_active_label(self):
        return self._active_lbl

    # ── DATA LOADING ─────────────────────────────────────────────────────────

    def _load_data(self):
        choice = LoadDataDialog(self)
        self.wait_window(choice)
        if not choice.result: return
        mode, items = choice.result
        self.session = AnnotationSession()
        self.session.mode  = mode
        self.session.items = items
        self.cur_idx = 0
        self._mode_var.set(mode if mode in ("image","text","csv") else "image")
        self._show_panel(mode)
        self._render_current()
        self._set_status(f"Loaded {len(items)} items — mode: {mode.upper()}")

    def _load_demo(self):
        """Pre-load demo labels so the app is immediately useful."""
        for name, key, shade in [
            ("Positive",  "1", LABEL_SHADES[0]),
            ("Negative",  "2", LABEL_SHADES[4]),
            ("Neutral",   "3", LABEL_SHADES[2]),
            ("Object",    "q", LABEL_SHADES[1]),
            ("Background","w", LABEL_SHADES[6]),
        ]:
            self.label_store.add(name, key, shade)
        self._refresh_labels()
        self._set_status("Demo labels loaded. Use LOAD DATA to begin.")

    # ── RENDER ───────────────────────────────────────────────────────────────

    def _render_current(self):
        if not self.session.items:
            self.item_title_var.set("No data loaded")
            return

        n = len(self.session.items)
        self.progress_var.set(f"{self.cur_idx+1} / {n}")
        self._draw_progress(self.cur_idx+1, n)

        item = self.session.items[self.cur_idx]
        item_id = str(self.cur_idx)
        annots  = self.session.get_annot(item_id)

        mode = self.session.mode

        if mode == "image":
            self.item_title_var.set(os.path.basename(str(item)))
            self.img_annotator.load_image(str(item), annots)
        elif mode == "text":
            self.item_title_var.set(f"Text item {self.cur_idx+1}")
            self.txt_annotator.load_text(str(item), annots)
        elif mode == "csv":
            self.item_title_var.set(f"Row {self.cur_idx+1}")
            self.csv_annotator.load_row(item if isinstance(item,dict) else {"value":item}, annots)

        self._refresh_annot_list(annots)

    def _draw_progress(self, current, total):
        self.prog_canvas.delete("all")
        w = self.prog_canvas.winfo_width() or 180
        filled = max(4, int(w * current / max(total,1)))
        self.prog_canvas.create_rectangle(0,0,w,6, fill=U["surface3"], outline="")
        self.prog_canvas.create_rectangle(0,0,filled,6, fill=U["accent"], outline="")

    def _refresh_annot_list(self, annots):
        self.annot_listbox.delete(0,"end")
        for a in annots:
            t    = a.get("type","?")
            lb   = a.get("label","?")
            d    = a.get("data",{})
            if t == "bbox":
                info = f"[{d['x1']:.0f},{d['y1']:.0f}→{d['x2']:.0f},{d['y2']:.0f}]"
            elif t == "point":
                info = f"[{d.get('x',0):.0f},{d.get('y',0):.0f}]"
            elif t == "span":
                info = f"\"{d.get('text','')[:18]}\""
            elif t == "classify":
                info = "[whole item]"
            elif t == "row":
                info = "[row]"
            else:
                info = ""
            self.annot_listbox.insert("end", f"  {t.upper()}  {lb}  {info}")
        self.annot_count_var.set(f"{len(annots)} annotation{'s' if len(annots)!=1 else ''}")

    # ── ANNOTATIONS ──────────────────────────────────────────────────────────

    def _on_new_annot(self, annot):
        item_id = str(self.cur_idx)
        self.session.add_annot(item_id, annot)
        annots = self.session.get_annot(item_id)
        self._refresh_annot_list(annots)

        mode = self.session.mode
        if mode == "image":
            self.img_annotator.refresh(annots)
        elif mode == "text":
            self.txt_annotator.refresh(annots)
        elif mode == "csv":
            item = self.session.items[self.cur_idx]
            self.csv_annotator.load_row(
                item if isinstance(item,dict) else {"value":item}, annots)

        self._set_status(f"Annotated: {annot['type'].upper()}  →  {annot['label']}")

    def _remove_selected_annot(self):
        sel = self.annot_listbox.curselection()
        if not sel: return
        item_id = str(self.cur_idx)
        self.session.remove_annot(item_id, sel[0])
        annots = self.session.get_annot(item_id)
        self._refresh_annot_list(annots)
        mode = self.session.mode
        if mode == "image": self.img_annotator.refresh(annots)
        elif mode == "text": self.txt_annotator.refresh(annots)

    def _clear_all_annots(self):
        if not messagebox.askyesno("Clear", "Clear all annotations for this item?",
                                    parent=self): return
        item_id = str(self.cur_idx)
        self.session.set_annot(item_id, [])
        self._refresh_annot_list([])
        mode = self.session.mode
        if mode == "image": self.img_annotator.refresh([])
        elif mode == "text": self.txt_annotator.refresh([])

    # ── NAVIGATION ───────────────────────────────────────────────────────────

    def _go_prev(self):
        if self.cur_idx > 0:
            self.cur_idx -= 1
            self._render_current()

    def _go_next(self):
        if self.cur_idx < len(self.session.items) - 1:
            self.cur_idx += 1
            self._render_current()

    def _jump(self, _=None):
        try:
            idx = int(self.jump_var.get()) - 1
            if 0 <= idx < len(self.session.items):
                self.cur_idx = idx
                self._render_current()
        except ValueError:
            pass
        self.jump_var.set("")

    # ── KEY SHORTCUTS ────────────────────────────────────────────────────────

    def _on_key(self, e):
        k = e.char
        if not k: return
        # Navigation
        if k in ("\x1b",):  # ESC
            self._active_lbl = None
            self._refresh_labels()
            return
        if e.keysym == "Left":  self._go_prev(); return
        if e.keysym == "Right": self._go_next(); return
        # Image draw modes
        if k == "q" and self.session.mode == "image":
            self.img_annotator._set_mode("BBOX"); return
        if k == "w" and self.session.mode == "image":
            self.img_annotator._set_mode("POINT"); return
        if k == "e" and self.session.mode == "image":
            self.img_annotator._set_mode("CLASSIFY"); return
        # Label shortcuts
        lb = self.label_store.by_key(k)
        if lb:
            self._select_label(lb)
            # For CSV / classify: auto-annotate immediately
            if self.session.mode == "csv" and self.session.items:
                self._on_new_annot({
                    "type":"row","label":lb["name"],
                    "shade":lb["shade"],"data":{}
                })
            elif self.session.mode == "image":
                mode = self.img_annotator._draw_mode
                if mode == "CLASSIFY":
                    self._on_new_annot({
                        "type":"classify","label":lb["name"],
                        "shade":lb["shade"],"data":{}
                    })

    # ── EXPORT / SESSION ─────────────────────────────────────────────────────

    def _export_coco(self):
        if not self.session.annots:
            messagebox.showinfo("Export","No annotations to export.",parent=self); return
        path = filedialog.asksaveasfilename(
            title="Export COCO Format",
            defaultextension=".json",
            filetypes=[("COCO JSON","*.json")])
        if not path: return
        self.session.export_coco(path, self.label_store)
        self._set_status(f"Exported COCO → {path}")

    def _export_yolo(self):
        if not self.session.annots:
            messagebox.showinfo("Export","No annotations to export.",parent=self); return
        path = filedialog.askdirectory(title="Select YOLO Export Directory")
        if not path: return
        self.session.export_yolo(path, self.label_store)
        self._set_status(f"Exported YOLO format directory → {path}")

    def _export_json(self):
        if not self.session.annots:
            messagebox.showinfo("Export","No annotations to export.",parent=self); return
        path = filedialog.asksaveasfilename(
            title="Export JSON",
            defaultextension=".json",
            filetypes=[("JSON","*.json")])
        if not path: return
        self.session.export_json(path)
        self._set_status(f"Exported JSON → {path}")

    def _export_csv(self):
        if not self.session.annots:
            messagebox.showinfo("Export","No annotations to export.",parent=self); return
        path = filedialog.asksaveasfilename(
            title="Export CSV",
            defaultextension=".csv",
            filetypes=[("CSV","*.csv")])
        if not path: return
        self.session.export_csv_flat(path)
        self._set_status(f"Exported CSV → {path}")

    def _save_session(self):
        path = filedialog.asksaveasfilename(
            title="Save Session",
            defaultextension=".ann",
            filetypes=[("Annotation Session","*.ann")])
        if not path: return
        data = {
            "labels":  self.label_store.to_list(),
            "session": self.session.to_dict(),
            "cur_idx": self.cur_idx,
        }
        with open(path,"w") as f:
            json.dump(data, f, indent=2)
        self._set_status(f"Session saved → {path}")

    def _load_session(self):
        path = filedialog.askopenfilename(
            title="Load Session",
            filetypes=[("Annotation Session","*.ann"),("All","*.*")])
        if not path: return
        try:
            with open(path) as f:
                data = json.load(f)
            self.label_store.from_list(data.get("labels",[]))
            self.session.from_dict(data.get("session",{}))
            self.cur_idx = data.get("cur_idx", 0)
            self._refresh_labels()
            if self.session.mode:
                self._mode_var.set(self.session.mode)
                self._show_panel(self.session.mode)
            self._render_current()
            self._set_status(f"Session loaded ← {path}")
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=self)

    # ── MISC ─────────────────────────────────────────────────────────────────

    def _on_mode_change(self):
        m = self._mode_var.get()
        self._show_panel(m)

    def _show_panel(self, mode):
        for p in [self.img_annotator, self.txt_annotator, self.csv_annotator]:
            p.pack_forget()
        if mode == "image":
            self.img_annotator.pack(fill="both", expand=True)
        elif mode == "text":
            self.txt_annotator.pack(fill="both", expand=True)
        elif mode == "csv":
            self.csv_annotator.pack(fill="both", expand=True)

    def _set_status(self, msg):
        self.status_var.set(msg)
