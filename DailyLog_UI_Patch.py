# === DailyLog UI Patch BEGIN ===
try:
    import tkinter as tk
    from tkinter import ttk
    import tkinter.font as tkfont
    _DL_DEFAULT_FAMILY = "Malgun Gothic"
    for _fam in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkTooltipFont"):
        try:
            _f = tkfont.nametofont(_fam); _f.configure(family=_DL_DEFAULT_FAMILY, size=10)
        except Exception:
            pass
    try:
        _style = ttk.Style()
        try:
            _style.theme_use("vista")
        except Exception:
            pass
        _style.configure("TButton", font=(_DL_DEFAULT_FAMILY, 10), padding=6)
    except Exception:
        pass
except Exception:
    pass

try:
    import PySimpleGUI as sg
    sg.theme("SystemDefaultForReal")
    sg.set_options(font=("Malgun Gothic", 10))
except Exception:
    pass

try:
    import customtkinter as ctk
    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")
except Exception:
    pass
# === DailyLog UI Patch END ===
