# ui/theme.py
"""
Applies the VS Code style dark theme (greys + purple accents) to ttk widgets.

All colours live in ui/palette.py - edit them there, not here.
"""
from tkinter import ttk

try:
    from ui import palette as P
except ImportError:
    import palette as P


def apply_dark_theme(root):
    """
    Apply the dark theme to the whole application.
    Call once in App.__init__ before laying out widgets.
    """
    root.configure(bg=P.BG)

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    # -------------------------
    # Base
    # -------------------------
    style.configure(".", background=P.BG, foreground=P.FG,
                    fieldbackground=P.SURFACE_ALT, borderwidth=0, relief="flat",
                    font=P.FONT)

    style.configure("TFrame", background=P.BG)
    style.configure("Card.TFrame", background=P.SURFACE)
    style.configure("Panel.TFrame", background=P.SURFACE_ALT)

    style.configure("TLabel", background=P.BG, foreground=P.FG)
    style.configure("Muted.TLabel", background=P.BG, foreground=P.FG_MUTED)
    style.configure("Title.TLabel", background=P.BG, foreground=P.FG_STRONG,
                    font=P.FONT_TITLE)

    # -------------------------
    # Buttons
    # -------------------------
    style.configure("TButton", background=P.SURFACE_ALT, foreground=P.FG,
                    padding=(12, 6), relief="flat", borderwidth=0, focusthickness=0)
    style.map("TButton",
              background=[("pressed", P.ACCENT_DIM), ("active", P.BORDER)],
              foreground=[("pressed", "#ffffff"), ("active", P.FG_STRONG)],
              relief=[("pressed", "flat"), ("!pressed", "flat")])

    style.configure("Accent.TButton", background=P.ACCENT, foreground="#ffffff",
                    padding=(14, 6), relief="flat", borderwidth=0)
    style.map("Accent.TButton",
              background=[("pressed", P.ACCENT_DIM), ("active", P.ACCENT_HOVER)],
              foreground=[("active", "#ffffff")])

    # -------------------------
    # Entries / Combobox
    # -------------------------
    style.configure("TEntry", fieldbackground=P.SURFACE_ALT, foreground=P.FG,
                    insertcolor=P.FG, padding=5, relief="flat",
                    bordercolor=P.BORDER, lightcolor=P.BORDER, darkcolor=P.BORDER)
    style.map("TEntry",
              bordercolor=[("focus", P.ACCENT)],
              lightcolor=[("focus", P.ACCENT)],
              darkcolor=[("focus", P.ACCENT)])

    for name in ("TCombobox", "Dark.TCombobox"):
        style.configure(name, fieldbackground=P.SURFACE_ALT, background=P.SURFACE_ALT,
                        foreground=P.FG, arrowcolor=P.FG_MUTED, padding=4,
                        relief="flat", bordercolor=P.BORDER,
                        lightcolor=P.BORDER, darkcolor=P.BORDER,
                        selectbackground=P.ACCENT, selectforeground="#ffffff")
        style.map(name,
                  fieldbackground=[("readonly", P.SURFACE_ALT),
                                   ("!disabled", P.SURFACE_ALT)],
                  foreground=[("readonly", P.FG)],
                  background=[("active", P.BORDER)],
                  arrowcolor=[("active", P.ACCENT_HOVER)],
                  bordercolor=[("focus", P.ACCENT)])

    # dropdown list of the combobox (a Tk listbox under the hood)
    root.option_add("*TCombobox*Listbox.background", P.SURFACE_ALT)
    root.option_add("*TCombobox*Listbox.foreground", P.FG)
    root.option_add("*TCombobox*Listbox.selectBackground", P.ACCENT)
    root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
    root.option_add("*TCombobox*Listbox.borderWidth", 0)

    # -------------------------
    # Notebook
    # -------------------------
    style.configure("TNotebook", background=P.BG, borderwidth=0)
    style.configure("TNotebook.Tab", background=P.SURFACE_ALT, foreground=P.FG_MUTED,
                    padding=(14, 7), borderwidth=0)
    style.map("TNotebook.Tab",
              background=[("selected", P.BG), ("active", P.BORDER)],
              foreground=[("selected", P.FG_STRONG)])

    # -------------------------
    # Progressbar
    # -------------------------
    style.configure("TProgressbar", background=P.ACCENT, troughcolor=P.SURFACE_ALT,
                    bordercolor=P.SURFACE_ALT, lightcolor=P.ACCENT,
                    darkcolor=P.ACCENT, thickness=6)

    # -------------------------
    # Treeview
    # -------------------------
    style.configure("Treeview", background=P.SURFACE, fieldbackground=P.SURFACE,
                    foreground=P.FG, rowheight=P.ROW_H, borderwidth=0)
    style.configure("Treeview.Heading", background=P.HEADER_BG,
                    foreground=P.HEADER_FG, borderwidth=0, relief="flat")
    style.map("Treeview",
              background=[("selected", P.ACCENT)],
              foreground=[("selected", "#ffffff")])

    # -------------------------
    # Scrollbars
    # -------------------------
    for orient in ("Vertical", "Horizontal"):
        style.configure(f"{orient}.TScrollbar", background=P.SURFACE_ALT,
                        troughcolor=P.BG, bordercolor=P.BG,
                        arrowcolor=P.FG_MUTED, gripcount=0,
                        lightcolor=P.SURFACE_ALT, darkcolor=P.SURFACE_ALT)
        style.map(f"{orient}.TScrollbar",
                  background=[("active", P.ACCENT_DIM), ("pressed", P.ACCENT)],
                  arrowcolor=[("active", P.FG_STRONG)])

    # -------------------------
    # Sidebar
    # -------------------------
    style.configure("Sidebar.TFrame", background=P.SIDEBAR)
    style.configure("Sidebar.TButton", background=P.SIDEBAR, foreground=P.FG_MUTED,
                    anchor="w", padding=(12, 10), relief="flat", borderwidth=0)
    style.map("Sidebar.TButton",
              background=[("active", P.SURFACE_ALT), ("pressed", P.SURFACE_ALT)],
              foreground=[("active", P.FG_STRONG)])

    style.configure("SidebarSelected.TButton", background=P.SURFACE_ALT,
                    foreground=P.ACCENT_TEXT, anchor="w", padding=(12, 10),
                    relief="flat", borderwidth=0)
    style.map("SidebarSelected.TButton",
              background=[("active", P.SURFACE_ALT)],
              foreground=[("active", P.ACCENT_HOVER)])

    return style
