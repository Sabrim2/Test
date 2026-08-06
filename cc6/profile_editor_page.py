# ui/profile_editor_page.py
"""
Create or edit a profile (file paths + output suffix + target address).
- Stores BOTH target_address_hex (for backend) and target_address_dotted (for UI).
- Does NOT store Start/End time.
- Uses LAZY imports to avoid circular/import-time errors.
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from profile_manager import save_profile, list_profiles

try:
    from ui import palette as P
except ImportError:
    import palette as P


class ProfileEditorPage(tk.Frame):
    """Create or edit a profile (file paths + suffix + target address)."""

    FIELD_KEYS = ("ixl_file", "cm_log_file", "pcap_file", "packetswitch_file",
                  "ixl_excel_file", "location_excel_file", "output_suffix",
                  "target_address_input")

    def __init__(self, parent, controller):
        super().__init__(parent, bg=P.BG)
        self.controller = controller

        main_container = tk.Frame(self, bg=P.BG)
        main_container.pack(fill="both", expand=True)

        self.form_container = tk.Frame(main_container, bg=P.BG)
        self.form_container.pack(side="left", fill="both", expand=True,
                                 padx=(16, 8), pady=16)

        # ---------------- right: profile list ----------------
        self.profile_panel = tk.Frame(main_container, bg=P.SURFACE, width=250,
                                      highlightthickness=1,
                                      highlightbackground=P.BORDER)
        self.profile_panel.pack(side="right", fill="y", padx=(8, 16), pady=16)
        self.profile_panel.pack_propagate(False)

        tk.Label(self.profile_panel, text="Profiles", bg=P.SURFACE,
                 fg=P.FG_STRONG, font=P.FONT_BOLD).pack(anchor="w", padx=14,
                                                        pady=(12, 6))

        self.profile_listbox = tk.Listbox(
            self.profile_panel, bg=P.BG, fg=P.FG,
            selectbackground=P.ACCENT, selectforeground="#ffffff",
            font=P.FONT, borderwidth=0, highlightthickness=1,
            highlightbackground=P.BORDER, activestyle="none")
        self.profile_listbox.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.profile_listbox.bind("<<ListboxSelect>>", self._on_profile_select)
        self._reload_list()

        # ---------------- left: form ----------------
        tk.Label(self.form_container, text="Create / Edit Profile",
                 font=P.FONT_TITLE, fg=P.FG_STRONG, bg=P.BG).pack(anchor="w")
        tk.Label(self.form_container,
                 text="Profiles save file paths, output suffix and target address "
                      "(time is chosen at run time).",
                 font=P.FONT, fg=P.FG_MUTED, bg=P.BG).pack(anchor="w", pady=(2, 14))

        card = tk.Frame(self.form_container, bg=P.SURFACE, highlightthickness=1,
                        highlightbackground=P.BORDER)
        card.pack(fill="both", expand=True)

        form = tk.Frame(card, bg=P.SURFACE)
        form.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        self._entries = {}
        row = 0

        def add_file_field(label, key, filetypes):
            nonlocal row
            tk.Label(form, text=label, fg=P.FG, bg=P.SURFACE, font=P.FONT).grid(
                row=row, column=0, sticky="w", pady=5, padx=(0, 12))
            e = ttk.Entry(form, width=56)
            e.grid(row=row, column=1, sticky="w", pady=5)
            ttk.Button(form, text="Browse",
                       command=lambda: self._browse_into(e, filetypes)).grid(
                row=row, column=2, padx=(10, 0))
            self._entries[key] = e
            row += 1

        def add_text_field(label, key, width=34):
            nonlocal row
            tk.Label(form, text=label, fg=P.FG, bg=P.SURFACE, font=P.FONT).grid(
                row=row, column=0, sticky="w", pady=5, padx=(0, 12))
            e = ttk.Entry(form, width=width)
            e.grid(row=row, column=1, sticky="w", pady=5)
            self._entries[key] = e
            row += 1

        add_file_field("IXL Text File", "ixl_file",
                       [("Text", "*.txt"), ("All", "*.*")])
        add_file_field("CM Log Text File", "cm_log_file",
                       [("Text", "*.txt"), ("All", "*.*")])
        add_file_field("Wireshark PCAP File", "pcap_file",
                       [("PCAP", "*.pcap"), ("All", "*.*")])
        add_file_field("Packetswitch File", "packetswitch_file",
                       [("HTML", "*.html"), ("DOCX", "*.docx"), ("All", "*.*")])
        add_file_field("Component Excel File", "ixl_excel_file",
                       [("Excel", "*.xlsx"), ("All", "*.*")])
        add_file_field("Location Excel File", "location_excel_file",
                       [("Excel", "*.xlsx"), ("All", "*.*")])

        add_text_field("Output Suffix", "output_suffix")
        add_text_field("Target Address (hex or dotted)", "target_address_input")

        tk.Label(form, text="Profile Name", fg=P.FG, bg=P.SURFACE,
                 font=P.FONT).grid(row=row, column=0, sticky="w",
                                   pady=(14, 5), padx=(0, 12))
        self.name_entry = ttk.Entry(form, width=34)
        self.name_entry.grid(row=row, column=1, sticky="w", pady=(14, 5))
        row += 1

        actions = tk.Frame(card, bg=P.SURFACE)
        actions.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 20))
        ttk.Button(actions, text="Save Profile", style="Accent.TButton",
                   command=self._save).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(actions, text="Back",
                   command=lambda: controller.show(self._start_page_class())
                   ).grid(row=0, column=1)

    # ------------------------
    # list helpers
    # ------------------------
    def _reload_list(self):
        self.profile_listbox.delete(0, tk.END)
        for p in sorted(list_profiles()):
            self.profile_listbox.insert("end", p)

    def load_blank(self):
        self.name_entry.delete(0, tk.END)
        for e in self._entries.values():
            e.delete(0, tk.END)

    def on_show(self):
        self._reload_list()
        self.load_blank()
        self.profile_listbox.selection_clear(0, tk.END)

    # ------------------------
    # internal helpers
    # ------------------------
    def _browse_into(self, entry, filetypes):
        initial = os.path.dirname(entry.get()) if entry.get() else os.getcwd()
        path = filedialog.askopenfilename(title="Select file", filetypes=filetypes,
                                          initialdir=initial)
        if path:
            entry.delete(0, tk.END)
            entry.insert(0, path)

    def _start_page_class(self):
        from ui.start_page import StartPage
        return StartPage

    def _on_profile_select(self, _event=None):
        selection = self.profile_listbox.curselection()
        if not selection:
            return
        self.load_profile_into_form(self.profile_listbox.get(selection[0]))

    def _compute_hex_and_dotted(self, addr_text: str):
        """
        Return (hex_str, dotted_str) from user input that may be dotted or hex.
        Dotted -> hex by removing dots and replacing '0' with 'a'
        (matching the backend address rule). Hex -> dotted via the backend helper.
        """
        try:
            from analyzer_backend import to_dotted_atcs_format
        except Exception as e:
            messagebox.showerror("Error", f"Could not load address formatter:\n{e}")
            return "", ""

        s = (addr_text or "").strip()
        if not s:
            return "", ""

        raw = s.replace(":", "").replace("-", "").replace(".", "")
        if "." in s:
            hex_str = raw.replace("0", "a")
            dotted_str = s
        else:
            hex_str = raw
            dotted_str = to_dotted_atcs_format(s)

        hex_str = "".join(c for c in hex_str if c.lower() in "0123456789abcdef")[:10]
        return hex_str, dotted_str

    def load_profile_into_form(self, name):
        from profile_manager import load_profile

        try:
            data = load_profile(name)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load profile '{name}':\n{e}")
            return

        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, name)

        for key in ("ixl_file", "cm_log_file", "pcap_file", "packetswitch_file",
                    "ixl_excel_file", "location_excel_file", "output_suffix"):
            self._entries[key].delete(0, tk.END)
            self._entries[key].insert(0, data.get(key, ""))

        self._entries["target_address_input"].delete(0, tk.END)
        self._entries["target_address_input"].insert(
            0, data.get("target_address_dotted", "")
               or data.get("target_address_hex", ""))

        for i in range(self.profile_listbox.size()):
            if self.profile_listbox.get(i) == name:
                self.profile_listbox.selection_clear(0, tk.END)
                self.profile_listbox.selection_set(i)
                self.profile_listbox.see(i)
                break

    def _save(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Enter a profile name.")
            return

        hex_addr, dotted_addr = self._compute_hex_and_dotted(
            self._entries["target_address_input"].get().strip())

        data = {
            "ixl_file":            self._entries["ixl_file"].get().strip(),
            "cm_log_file":         self._entries["cm_log_file"].get().strip(),
            "pcap_file":           self._entries["pcap_file"].get().strip(),
            "packetswitch_file":   self._entries["packetswitch_file"].get().strip(),
            "ixl_excel_file":      self._entries["ixl_excel_file"].get().strip(),
            "location_excel_file": self._entries["location_excel_file"].get().strip(),
            "output_suffix":       self._entries["output_suffix"].get().strip(),
            "target_address_hex":    hex_addr,
            "target_address_dotted": dotted_addr,
        }

        try:
            save_profile(name, data)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save profile:\n{e}")
            return

        self._reload_list()
        messagebox.showinfo("Saved", f"Profile '{name}' saved.")
        self.controller.refresh_start_page_profiles()
        self.controller.show(self._start_page_class())
