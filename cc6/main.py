# main.py
import os
import sys
import tkinter as tk
from tkinter import ttk

from ui import palette as P
from ui.theme import apply_dark_theme
from ui.sidebar import Sidebar
from ui.start_page import StartPage
from ui.profile_editor_page import ProfileEditorPage
from ui.run_analysis_page import RunAnalysisPage
from ui.results_page import ResultsPage


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Log Packet Analysis Tool")
        self._configure_dpi_awareness()
        self.geometry("1360x780")
        self.minsize(1040, 660)

        self.state = {
            "current_profile_name": None,
            "last_output_path": None,
        }

        apply_dark_theme(self)
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # Sidebar container (reserves the 60px gutter the overlay sits in)
        self.sidebar_container = ttk.Frame(self, style="Sidebar.TFrame")
        self.sidebar_container.grid(row=0, column=0, sticky="nsw")
        self.sidebar_container.configure(width=60)
        self.sidebar_container.grid_propagate(False)

        # Content container
        self.content_container = ttk.Frame(self, padding=(4, 0, 4, 0))
        self.content_container.grid(row=0, column=1, sticky="nsew")
        self.content_container.columnconfigure(0, weight=1)
        self.content_container.rowconfigure(0, weight=1)

        os.makedirs("profiles", exist_ok=True)

        self.pages = {}
        for PageClass in (StartPage, ProfileEditorPage, RunAnalysisPage, ResultsPage):
            frame = PageClass(self.content_container, controller=self)
            self.pages[PageClass] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        # ========================
        # SIDEBAR
        # ========================
        nav_items = [
            ("Profiles", StartPage),
            ("Run Analysis", RunAnalysisPage),
            ("Edit Profile", ProfileEditorPage),
            ("Results Page", ResultsPage),
        ]

        self.sidebar = Sidebar(self, self, nav_items)
        self.sidebar.place(x=0, y=0, relheight=1)
        self.sidebar.lift()

        self.show(StartPage)

    # ------------------------------------------------------------------
    def show(self, page_class):
        frame = self.pages[page_class]
        frame.tkraise()

        if hasattr(self, "sidebar"):
            self.sidebar.highlight(page_class)

        if hasattr(frame, "on_show") and callable(frame.on_show):
            frame.on_show()

    def show_results(self, xlsx_path):
        """Load a finished analysis into the results page and jump to it."""
        page = self.pages[ResultsPage]
        self.state["last_output_path"] = xlsx_path
        if page.load_results(xlsx_path):
            self.show(ResultsPage)

    def refresh_start_page_profiles(self):
        start_page = self.pages.get(StartPage)
        if start_page and hasattr(start_page, "reload_profiles"):
            from profile_manager import list_profiles
            start_page.reload_profiles(list_profiles())

    def _configure_dpi_awareness(self):
        if sys.platform.startswith("win"):
            try:
                import ctypes
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                pass


if __name__ == "__main__":
    App().mainloop()
