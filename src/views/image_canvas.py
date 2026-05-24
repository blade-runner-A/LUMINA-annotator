import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
from ..config import U, LABEL_TEXT_FOR
from ..ui_helpers import _label, _sep

class ImageCanvas(tk.Frame):
    """Handles image display + bbox / point / polygon annotation drawing."""

    MODES = ["BBOX", "POLYGON", "POINT", "CLASSIFY"]

    def __init__(self, parent, on_new_annot, get_active_label, **kw):
        super().__init__(parent, bg=U["bg"], **kw)
        self.on_new_annot   = on_new_annot
        self.get_active_lbl = get_active_label
        self._draw_mode = "BBOX"
        self._img_orig  = None
        self._img_tk    = None
        self._scale     = 1.0
        self._offset    = (0, 0)
        self._annots    = []   # list of annotation dicts from session
        self._drag      = None
        self._cur_rect  = None
        self._poly_pts  = []   # Current polygon points (x, y)
        self._poly_draw = []   # Temporary canvas line IDs

        # toolbar
        tb = tk.Frame(self, bg=U["surface2"])
        tb.pack(fill="x")
        _label(tb, "DRAW MODE:", bg=U["surface2"], fg=U["text3"]).pack(side="left", padx=(10,6), pady=6)
        self._mode_var = tk.StringVar(value="BBOX")
        for m in self.MODES:
            rb = tk.Radiobutton(tb, text=m, variable=self._mode_var, value=m,
                                bg=U["surface2"], fg=U["text2"],
                                selectcolor=U["surface3"],
                                activebackground=U["surface2"],
                                font=("Courier",7,"bold"),
                                relief="flat", indicatoron=False,
                                padx=8, pady=4,
                                highlightthickness=0,
                                command=lambda _m=m: self._set_mode(_m))
            rb.pack(side="left", padx=2)
        _label(tb, "  [Q] bbox  [W] point  [E] classify",
               bg=U["surface2"], fg=U["text3"], size=6).pack(side="right", padx=10)

        _sep(self).pack(fill="x")

        # canvas
        self.canvas = tk.Canvas(self, bg="#111111",
                                 highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<ButtonPress-1>",   self._on_press)
        self.canvas.bind("<ButtonPress-3>",   self._on_right_click) # Close polygon
        self.canvas.bind("<B1-Motion>",       self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Configure>",       self._on_resize)

    def _set_mode(self, m):
        self._draw_mode = m
        self._clear_temp_poly()
        self._mode_var.set(m)
        curs = {"BBOX":"crosshair","POLYGON":"crosshair","POINT":"cross","CLASSIFY":"arrow"}
        self.canvas.config(cursor=curs.get(m,"crosshair"))

    def _clear_temp_poly(self):
        for line in self._poly_draw:
            self.canvas.delete(line)
        self._poly_pts = []
        self._poly_draw = []

    def load_image(self, path, annots):
        self._annots = annots
        try:
            self._img_orig = Image.open(path).convert("RGB")
        except Exception as ex:
            self._img_orig = None
            self.canvas.delete("all")
            self.canvas.create_text(10, 10, text=f"Error: {ex}",
                                     fill=U["text2"], anchor="nw",
                                     font=("Courier",9))
            return
        self._render()

    def refresh(self, annots):
        self._annots = annots
        self._render()

    def _render(self):
        if not self._img_orig: return
        cw = self.canvas.winfo_width()  or 600
        ch = self.canvas.winfo_height() or 500
        iw, ih = self._img_orig.size
        scale = min(cw/iw, ch/ih, 1.0)
        self._scale = scale
        nw, nh = int(iw*scale), int(ih*scale)
        ox = (cw - nw)//2
        oy = (ch - nh)//2
        self._offset = (ox, oy)

        disp = self._img_orig.resize((nw, nh), Image.LANCZOS)
        self._img_tk = ImageTk.PhotoImage(disp)
        self.canvas.delete("all")
        self.canvas.create_image(ox, oy, anchor="nw", image=self._img_tk)
        self._draw_annots()

    def _draw_annots(self):
        ox, oy = self._offset
        s      = self._scale
        for a in self._annots:
            lb   = a.get("label","?")
            # find shade
            shade = a.get("shade","#aaa")
            txt_c = LABEL_TEXT_FOR.get(shade, "#eee")
            d = a.get("data",{})
            if a["type"] == "bbox":
                x1 = ox + d["x1"]*s; y1 = oy + d["y1"]*s
                x2 = ox + d["x2"]*s; y2 = oy + d["y2"]*s
                self.canvas.create_rectangle(x1,y1,x2,y2,
                    outline=shade, width=1)
                self.canvas.create_rectangle(x1,y1,x1+len(lb)*6+8,y1+14,
                    fill=shade, outline="")
                self.canvas.create_text(x1+4, y1+7, text=lb,
                    fill=txt_c, font=("Courier",7,"bold"), anchor="w")
            elif a["type"] == "point":
                px = ox + d["x"]*s; py = oy + d["y"]*s
                r = 5
                self.canvas.create_oval(px-r,py-r,px+r,py+r,
                    fill=shade, outline="")
                self.canvas.create_text(px+8, py,
                    text=lb, fill=shade,
                    font=("Courier",7,"bold"), anchor="w")
            elif a["type"] == "polygon":
                pts = d["points"]
                c_pts = []
                for pt in pts:
                    c_pts.extend([ox + pt[0]*s, oy + pt[1]*s])
                self.canvas.create_polygon(*c_pts, outline=shade, fill="", width=2)
                self.canvas.create_text(c_pts[0], c_pts[1]-10,
                    text=lb, fill=txt_c, font=("Courier",7,"bold"), anchor="w")

    def _canvas_to_img(self, cx, cy):
        ox, oy = self._offset
        s = self._scale
        return (cx - ox) / s, (cy - oy) / s

    def _on_press(self, e):
        if self._draw_mode == "BBOX":
            self._drag = (e.x, e.y)
        elif self._draw_mode == "POLYGON":
            lbl = self.get_active_lbl()
            if not lbl:
                messagebox.showinfo("No Label", "Select a label first.", parent=self)
                return
            self._poly_pts.append((e.x, e.y))
            if len(self._poly_pts) > 1:
                p1 = self._poly_pts[-2]
                p2 = self._poly_pts[-1]
                line = self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill=lbl["shade"], width=2)
                self._poly_draw.append(line)
        elif self._draw_mode == "POINT":
            lbl = self.get_active_lbl()
            if not lbl:
                messagebox.showinfo("No Label", "Select a label first.", parent=self)
                return
            ix, iy = self._canvas_to_img(e.x, e.y)
            if not self._img_orig: return
            iw, ih = self._img_orig.size
            if 0 <= ix <= iw and 0 <= iy <= ih:
                self.on_new_annot({
                    "type":"point","label":lbl["name"],
                    "shade": lbl["shade"],
                    "data":{"x":round(ix,1),"y":round(iy,1)}
                })
        elif self._draw_mode == "CLASSIFY":
            lbl = self.get_active_lbl()
            if not lbl:
                messagebox.showinfo("No Label", "Select a label first.", parent=self)
                return
            self.on_new_annot({
                "type":"classify","label":lbl["name"],
                "shade": lbl["shade"],
                "data":{}
            })

    def _on_right_click(self, e):
        if self._draw_mode == "POLYGON" and len(self._poly_pts) > 2:
            lbl = self.get_active_lbl()
            if not lbl: return
            
            # Close the polygon visually (temporary)
            p1 = self._poly_pts[-1]
            p2 = self._poly_pts[0]
            line = self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill=lbl["shade"], width=2)
            self._poly_draw.append(line)
            
            # Convert to img coords
            img_pts = []
            for px, py in self._poly_pts:
                ix, iy = self._canvas_to_img(px, py)
                img_pts.append([round(ix, 1), round(iy, 1)])
                
            self.on_new_annot({
                "type":"polygon","label":lbl["name"],
                "shade": lbl["shade"],
                "data":{"points": img_pts}
            })
            self._clear_temp_poly()
        elif self._draw_mode == "POLYGON":
            self._clear_temp_poly()

    def _on_drag(self, e):
        if self._draw_mode != "BBOX" or not self._drag: return
        if self._cur_rect:
            self.canvas.delete(self._cur_rect)
        x0,y0 = self._drag
        self._cur_rect = self.canvas.create_rectangle(
            x0,y0,e.x,e.y, outline="#aaa", dash=(4,4), width=1)

    def _on_release(self, e):
        if self._draw_mode != "BBOX" or not self._drag: return
        lbl = self.get_active_lbl()
        if not lbl:
            messagebox.showinfo("No Label", "Select a label first.", parent=self)
            if self._cur_rect: self.canvas.delete(self._cur_rect)
            self._drag = None; self._cur_rect = None
            return
        x0,y0 = self._drag
        x1,y1 = e.x, e.y
        if abs(x1-x0) < 5 or abs(y1-y0) < 5:
            if self._cur_rect: self.canvas.delete(self._cur_rect)
            self._drag = None; self._cur_rect = None
            return
        ix0,iy0 = self._canvas_to_img(min(x0,x1), min(y0,y1))
        ix1,iy1 = self._canvas_to_img(max(x0,x1), max(y0,y1))
        self.on_new_annot({
            "type":"bbox","label":lbl["name"],
            "shade": lbl["shade"],
            "data":{"x1":round(ix0,1),"y1":round(iy0,1),
                    "x2":round(ix1,1),"y2":round(iy1,1)}
        })
        if self._cur_rect: self.canvas.delete(self._cur_rect)
        self._drag = None; self._cur_rect = None

    def _on_resize(self, _):
        self.after(30, self._render)
