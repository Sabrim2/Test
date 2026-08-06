# ui/start_page.py
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox

from profile_manager import list_profiles, load_profile, PROFILE_DIR

try:
    from ui import palette as P
except ImportError:
    import palette as P


class StartPage(tk.Frame):
    """
    Landing page:
      - Select an existing profile and load it
      - Create a new profile
      - Manage profiles (refresh / delete / open folder)
    """

    def __init__(self, parent, controller):
        super().__init__(parent, bg=P.BG)
        self.controller = controller

        # --- header ---
        tk.Label(self, text="Log Analysis Profiles", font=P.FONT_TITLE,
                 fg=P.FG_STRONG, bg=P.BG).pack(anchor="w", padx=16, pady=(14, 2))
        tk.Label(self, text="Choose a saved configuration or create a new one",
                 font=P.FONT, fg=P.FG_MUTED, bg=P.BG).pack(anchor="w", padx=16,
                                                           pady=(0, 14))

        card = tk.Frame(self, bg=P.SURFACE, highlightthickness=1,
                        highlightbackground=P.BORDER)
        card.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        card.columnconfigure(0, weight=0)
        card.columnconfigure(1, weight=1)
        card.rowconfigure(0, weight=1)

        # --- left: controls ---
        left = tk.Frame(card, bg=P.SURFACE)
        left.grid(row=0, column=0, sticky="nw", padx=20, pady=20)

        tk.Label(left, text="Select Profile", fg=P.FG, bg=P.SURFACE,
                 font=P.FONT).grid(row=0, column=0, sticky="w")
        self.profile_combo = ttk.Combobox(left, width=42, values=list_profiles(),
                                          state="readonly")
        self.profile_combo.grid(row=1, column=0, sticky="w", pady=(6, 12))
        self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_selected)

        btns = tk.Frame(left, bg=P.SURFACE)
        btns.grid(row=2, column=0, sticky="w")
        ttk.Button(btns, text="Load Profile", style="Accent.TButton",
                   command=self._load_clicked).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(btns, text="Create New Profile",
                   command=self._new_clicked).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(btns, text="Refresh",
                   command=self._refresh_clicked).grid(row=0, column=2)

        mgmt = tk.Frame(left, bg=P.SURFACE)
        mgmt.grid(row=3, column=0, sticky="w", pady=(14, 0))
        ttk.Button(mgmt, text="Delete Profile",
                   command=self._delete_clicked).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(mgmt, text="Open Profiles Folder",
                   command=self._open_folder).grid(row=0, column=1)

        # --- right: preview ---
        right = tk.Frame(card, bg=P.SURFACE)
        right.grid(row=0, column=1, sticky="nsew", padx=(0, 20), pady=20)

        tk.Label(right, text="Profile Details", font=P.FONT_BOLD,
                 fg=P.FG_STRONG, bg=P.SURFACE).pack(anchor="w")
        self.preview = tk.Text(right, height=14, bg=P.BG, fg=P.FG,
                               insertbackground=P.FG, relief="flat", bd=0,
                               font=P.FONT, highlightthickness=1,
                               highlightbackground=P.BORDER, padx=12, pady=10)
        self.preview.pack(fill="both", expand=True, pady=(8, 0))
        self.preview.tag_configure("key", foreground=P.ACCENT_TEXT)
        self.preview.config(state="disabled")

    # -----------------
    # Page lifecycle
    # -----------------
    def on_show(self):
        self.reload_profiles(list_profiles())

    def reload_profiles(self, names):
        current = self.profile_combo.get()
        self.profile_combo["values"] = list(sorted(names))
        self.profile_combo.set(current if current in names else "")
        self._clear_preview()

    # -----------------
    # Actions
    # -----------------
    def _on_profile_selected(self, _evt=None):
        name = self.profile_combo.get()
        if not name:
            self._clear_preview()
            return
        try:
            data = load_profile(name)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load profile '{name}':\n{e}")
            return
        self._show_preview(name, data)

    def _load_clicked(self):
        name = self.profile_combo.get()
        if not name:
            messagebox.showerror("Error", "Please select a profile to load.")
            return
        self.controller.state["current_profile_name"] = name
        RunAnalysisPage = self._run_page_class()
        self.controller.pages[RunAnalysisPage].load_profile(name)
        self.controller.show(RunAnalysisPage)

    def _new_clicked(self):
        self.controller.show(self._editor_page_class())

    def _refresh_clicked(self):
        self.reload_profiles(list_profiles())

    def _delete_clicked(self):
        name = self.profile_combo.get()
        if not name:
            messagebox.showerror("Error", "Select a profile to delete.")
            return
        if messagebox.askyesno("Confirm",
                               f"Delete profile '{name}'? This cannot be undone."):
            try:
                os.remove(os.path.join(PROFILE_DIR, f"{name}.json"))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete profile:\n{e}")
            self.reload_profiles(list_profiles())

    def _open_folder(self):
        try:
            if sys.platform.startswith("win"):
                os.startfile(PROFILE_DIR)                      # noqa
            elif sys.platform == "darwin":
                import subprocess
                subprocess.run(["open", PROFILE_DIR], check=False)
            else:
                import subprocess
                subprocess.run(["xdg-open", PROFILE_DIR], check=False)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder:\n{e}")

    # -----------------
    # Helpers (lazy imports prevent circulars)
    # -----------------
    def _editor_page_class(self):
        from ui.profile_editor_page import ProfileEditorPage
        return ProfileEditorPage

    def _run_page_class(self):
        from ui.run_analysis_page import RunAnalysisPage
        return RunAnalysisPage

    def _clear_preview(self):
        self.preview.config(state="normal")
        self.preview.delete("1.0", tk.END)
        self.preview.insert("1.0", "No profile selected.")
        self.preview.config(state="disabled")

    def _show_preview(self, name, data):
        fields = [
            ("Name", name),
            ("IXL File", data.get("ixl_file", "")),
            ("CM Log File", data.get("cm_log_file", "")),
            ("PCAP File", data.get("pcap_file", "")),
            ("Packetswitch File", data.get("packetswitch_file", "")),
            ("Component Excel File", data.get("ixl_excel_file", "")),
            ("Location Excel File", data.get("location_excel_file", "")),
            ("Output Suffix", data.get("output_suffix", "")),
            ("Target Address (dotted)", data.get("target_address_dotted", "")),
            ("Target Address (hex)", data.get("target_address_hex", "")),
        ]

        self.preview.config(state="normal")
        self.preview.delete("1.0", tk.END)
        for label, value in fields:
            if not value:
                continue
            self.preview.insert("end", f"{label}: ", "key")
            self.preview.insert("end", f"{value}\n")
        self.preview.config(state="disabled")
