import tkinter as tk
from .config import U

def _btn(parent, text, cmd, accent=False, small=False, **kw):
    bg = U["accent"] if accent else U["surface3"]
    fg = U["bg"]     if accent else U["text2"]
    f  = ("Courier", 7 if small else 8, "bold")
    b = tk.Button(parent, text=text, command=cmd,
                  bg=bg, fg=fg, relief="flat",
                  font=f, padx=kw.pop("padx",8),
                  pady=kw.pop("pady",5),
                  activebackground=U["white"] if accent else U["border2"],
                  activeforeground=U["bg"] if accent else U["text"],
                  cursor="hand2", **kw)
    return b

def _label(parent, text, size=7, fg=None, bold=False, **kw):
    font = ("Courier", size, "bold" if bold else "normal")
    return tk.Label(parent, text=text,
                    bg=kw.pop("bg", U["surface"]),
                    fg=fg or U["text3"],
                    font=font, **kw)

def _sep(parent, vertical=False, color=None):
    kw = dict(bg=color or U["border"])
    if vertical: kw["width"]  = 1
    else:        kw["height"] = 1
    return tk.Frame(parent, **kw)

def _entry(parent, var, **kw):
    return tk.Entry(parent, textvariable=var,
                    bg=U["input"], fg=U["text"],
                    insertbackground=U["text"],
                    relief="flat", bd=0,
                    font=("Courier", 8),
                    highlightthickness=1,
                    highlightbackground=U["border"],
                    highlightcolor=U["border2"],
                    **kw)
