# ui/sidebar.py
import os
import tkinter as tk
from tkinter import ttk

try:
    from ui import palette as P
except ImportError:
    import palette as P

try:
    from PIL import Image, ImageTk
except ImportError:          # icons are optional
    Image = ImageTk = None


# icon file + fallback glyph for each nav entry
ICONS = {
    "Profiles":     ("icons/home.png",      "☰"),
    "Run Analysis": ("icons/play.png",      "▶"),
    "Edit Profile": ("icons/edit-icon.png", "✎"),
    "Results Page": ("icons/table.png",     "▦"),
}


class Sidebar(ttk.Frame):
    def __init__(self, parent, controller, pages):
        super().__init__(parent, style="Sidebar.TFrame")

        self.controller = controller
        self.animating = False
        self.state = "collapsed"

        self.expanded_width = 200
        self.collapsed_width = 60
        self.current_width = self.collapsed_width
        self.target_width = self.collapsed_width

        self.place(x=0, y=0, width=self.collapsed_width, relheight=1)

        self.icons = {}
        for name, (path, _glyph) in ICONS.items():
            self.icons[name] = self.load_icon(path)

        self._buttons = {}
        self._active = None

        for name, PageClass in pages:
            row = tk.Frame(self, bg=P.SIDEBAR, height=44)
            row.pack(fill="x", pady=4)
            row.pack_propagate(False)

            marker = tk.Frame(row, bg=P.SIDEBAR, width=3)
            marker.pack(side="left", fill="y")

            icon = self.icons.get(name)
            glyph = ICONS.get(name, (None, "●"))[1]

            btn = ttk.Button(
                row,
                text="" if icon else f" {glyph}",
                image=icon,
                compound="left",
                command=lambda p=PageClass: self._on_nav(p),
                style="Sidebar.TButton",
                takefocus=False,
            )
            btn.pack(side="left", fill="both", expand=True, padx=(3, 6))

            self._buttons[PageClass] = (btn, name, marker, glyph, icon)

        self.bind("<Enter>", self._expand)

    # ---------------- icons ----------------
    def load_icon(self, path):
        if ImageTk is None or not os.path.isfile(path):
            return None
        try:
            img = Image.open(path).resize((22, 22))
            return ImageTk.PhotoImage(img)
        except Exception:
            return None

    # ---------------- navigation ----------------
    def _on_nav(self, PageClass):
        if hasattr(self.controller, "show_frame"):
            self.controller.show_frame(PageClass.__name__)
        else:
            self.controller.show(PageClass)
        self.highlight(PageClass)

    def highlight(self, active):
        self._active = active
        for PageClass, (btn, _n, marker, _g, _i) in self._buttons.items():
            selected = PageClass == active
            btn.configure(style="SidebarSelected.TButton" if selected
                          else "Sidebar.TButton")
            marker.configure(bg=P.ACCENT if selected else P.SIDEBAR)

    # ---------------- expand / collapse ----------------
    def _label_for(self, name, glyph, icon, expanded):
        if expanded:
            return f"  {name}" if icon else f" {glyph}  {name}"
        return "" if icon else f" {glyph}"

    def _expand(self, event=None):
        if self.state == "expanded" or self.animating:
            return
        self.state = "expanded"
        for btn, name, _m, glyph, icon in self._buttons.values():
            btn.configure(text=self._label_for(name, glyph, icon, True))
        self.animate(self.expanded_width)
        self.after(50, self._track_mouse)

    def _collapse(self):
        if self.state == "collapsed":
            return
        self.state = "collapsed"
        for btn, name, _m, glyph, icon in self._buttons.values():
            btn.configure(text=self._label_for(name, glyph, icon, False))
        self.animate(self.collapsed_width)

    def _track_mouse(self):
        if self.state != "expanded":
            return
        x, y = self.winfo_pointerxy()
        left = self.winfo_rootx()
        right = left + self.current_width
        top = self.winfo_rooty()
        bottom = top + self.winfo_height()
        if not ((left <= x <= right) and (top <= y <= bottom)):
            self._collapse()
            return
        self.after(50, self._track_mouse)

    # ---------------- animation ----------------
    def animate(self, target_width):
        self.target_width = target_width
        if self.animating:
            return
        self.animating = True

        def step():
            diff = self.target_width - self.current_width
            if abs(diff) < 2:
                self.current_width = self.target_width
            else:
                self.current_width += diff * 0.3
            self.current_width = int(self.current_width)
            self.place_configure(width=self.current_width)
            if self.current_width != self.target_width:
                self.after(10, step)
            else:
                self.animating = False

        step()
