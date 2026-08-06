# ui/run_analysis_page.py
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from profile_manager import load_profile
from analyzer_backend import _normalize_atcs, to_dotted_atcs_format, load_location_excel_mapping

try:
    from ui import palette as P
except ImportError:
    import palette as P


class ProgressDialog(tk.Toplevel):
    def __init__(self, parent, title="Working...", message="Please wait..."):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=P.SURFACE)
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", lambda: None)
        self.transient(parent)
        self.grab_set()

        tk.Label(self, text=message, fg=P.FG, bg=P.SURFACE,
                 font=P.FONT).pack(padx=22, pady=(18, 10))
        self.pb = ttk.Progressbar(self, mode="indeterminate", length=280)
        self.pb.pack(padx=22, pady=(0, 18))
        self.pb.start(10)

        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() // 2 - self.winfo_width() // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2 - self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")


class RunAnalysisPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=P.BG)
        self.controller = controller

        tk.Label(self, text="Run Analysis", font=P.FONT_TITLE,
                 fg=P.FG_STRONG, bg=P.BG).pack(anchor="w", padx=16, pady=(14, 4))
        tk.Label(self, text="Pick the logs to compare, then run. "
                            "Results open in the app when the run finishes.",
                 font=P.FONT, fg=P.FG_MUTED, bg=P.BG).pack(anchor="w", padx=16,
                                                           pady=(0, 12))

        card = tk.Frame(self, bg=P.SURFACE, highlightthickness=1,
                        highlightbackground=P.BORDER)
        card.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        form = tk.Frame(card, bg=P.SURFACE)
        form.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

        self.fields = {}
        row = 0

        def add_file(label, key, filetypes):
            nonlocal row
            tk.Label(form, text=label, fg=P.FG, bg=P.SURFACE, font=P.FONT).grid(
                row=row, column=0, sticky="w", pady=5, padx=(0, 12))
            e = ttk.Entry(form, width=58)
            e.grid(row=row, column=1, sticky="w", pady=5)
            ttk.Button(form, text="Browse",
                       command=lambda: self._browse_into(e, filetypes)).grid(
                row=row, column=2, padx=(10, 0))
            self.fields[key] = e
            row += 1

        add_file("IXL Text File", "ixl_file", [("Text", "*.txt"), ("All", "*.*")])
        add_file("CM Log Text File", "cm_log_file", [("Text", "*.txt"), ("All", "*.*")])
        add_file("Wireshark PCAP File", "pcap_file", [("PCAP", "*.pcap"), ("All", "*.*")])
        add_file("Packetswitch File", "packetswitch_file",
                 [("HTML", "*.html"), ("DOCX", "*.docx"), ("All", "*.*")])
        add_file("Component Excel File", "ixl_excel_file",
                 [("Excel", "*.xlsx"), ("All", "*.*")])
        add_file("Location Excel File", "location_excel_file",
                 [("Excel", "*.xlsx"), ("All", "*.*")])

        tk.Label(form, text="Filename Suffix", fg=P.FG, bg=P.SURFACE,
                 font=P.FONT).grid(row=row, column=0, sticky="w", pady=5, padx=(0, 12))
        self.suffix_entry = ttk.Entry(form, width=58)
        self.suffix_entry.grid(row=row, column=1, sticky="w", pady=5)
        row += 1

        tk.Label(form, text="Target Address", fg=P.FG, bg=P.SURFACE,
                 font=P.FONT).grid(row=row, column=0, sticky="w", pady=5, padx=(0, 12))
        self.addr_combo = ttk.Combobox(form, width=26, state="normal")
        self.addr_combo.grid(row=row, column=1, sticky="w", pady=5)
        ttk.Button(form, text="Scan Addresses & Time",
                   command=self._scan_pcap_metadata).grid(row=row, column=2,
                                                          padx=(10, 0))
        row += 1

        tk.Label(form, text="Start Time (HH:MM:SS.sss)", fg=P.FG, bg=P.SURFACE,
                 font=P.FONT).grid(row=row, column=0, sticky="w", pady=5, padx=(0, 12))
        self.start_time_entry = ttk.Entry(form, width=26)
        self.start_time_entry.grid(row=row, column=1, sticky="w", pady=5)
        row += 1

        tk.Label(form, text="End Time (HH:MM:SS.sss)", fg=P.FG, bg=P.SURFACE,
                 font=P.FONT).grid(row=row, column=0, sticky="w", pady=5, padx=(0, 12))
        self.end_time_entry = ttk.Entry(form, width=26)
        self.end_time_entry.grid(row=row, column=1, sticky="w", pady=5)
        row += 1

        actions = tk.Frame(card, bg=P.SURFACE)
        actions.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 20))
        ttk.Button(actions, text="Run Analysis", style="Accent.TButton",
                   command=self._run).grid(row=0, column=0)
        ttk.Button(actions, text="View last results",
                   command=self._view_last).grid(row=0, column=1, padx=(10, 0))

    # ---------------- helpers ----------------
    def _browse_into(self, entry, filetypes):
        path = filedialog.askopenfilename(title="Select file", filetypes=filetypes)
        if path:
            entry.delete(0, tk.END)
            entry.insert(0, path)

    def _view_last(self):
        path = (self.controller.state or {}).get("last_output_path")
        if not path:
            messagebox.showinfo("Results", "No analysis has been run yet.")
            return
        self.controller.show_results(path)

    # ---------------- pcap scan ----------------
    def _scan_pcap_metadata(self):
        pcap_entry = self.fields.get("pcap_file")
        pcap_path = pcap_entry.get().strip() if pcap_entry else ""
        if not pcap_path:
            messagebox.showerror("Error", "Please select a PCAP file first.")
            return

        dlg = ProgressDialog(self, title="Scanning PCAP",
                             message="Scanning PCAP for addresses and time range...")

        def worker():
            dropdown_values = []
            start_time = end_time = None
            err = None
            try:
                from analyzer_backend import (
                    collect_atcs_addresses_starting_with7,
                    to_dotted_atcs_format,
                    find_pcap_time_bounds,
                )

                raw_addrs = collect_atcs_addresses_starting_with7(pcap_path)
                location_excel_path = self.fields["location_excel_file"].get().strip()
                excel_map = load_location_excel_mapping(location_excel_path)

                seen = set()
                for addr in raw_addrs:
                    dotted = to_dotted_atcs_format(addr)
                    if not dotted:
                        continue
                    norm = _normalize_atcs(dotted)
                    display = excel_map.get(norm, dotted)
                    if display not in seen:
                        seen.add(display)
                        dropdown_values.append(display)

                start_time, end_time = find_pcap_time_bounds(pcap_path)
            except Exception as e:
                err = str(e)

            def done():
                try:
                    if err:
                        messagebox.showerror("Error", f"Failed to scan PCAP:\n{err}")
                        return
                    current_addr = self.addr_combo.get()
                    self.addr_combo["values"] = dropdown_values
                    self.addr_combo.set(current_addr)
                    if start_time:
                        self.start_time_entry.delete(0, tk.END)
                        self.start_time_entry.insert(0, start_time)
                    if end_time:
                        self.end_time_entry.delete(0, tk.END)
                        self.end_time_entry.insert(0, end_time)
                finally:
                    dlg.destroy()

            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    # ---------------- profile ----------------
    def load_profile(self, name):
        try:
            data = load_profile(name)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load profile '{name}':\n{e}")
            return

        def setf(key, val):
            w = self.fields.get(key)
            if w is not None:
                w.delete(0, tk.END)
                if val:
                    w.insert(0, val)

        for key in ("ixl_file", "cm_log_file", "pcap_file", "packetswitch_file",
                    "ixl_excel_file", "location_excel_file"):
            setf(key, data.get(key))

        self.profile_suffix = data.get("output_suffix", "")
        self.suffix_entry.delete(0, tk.END)
        self.suffix_entry.insert(0, self.profile_suffix)

        self.addr_combo.set(data.get("target_address_dotted") or "")

    # ---------------- run ----------------
    def _run(self):
        from analyzer_backend import analyze_logs, resolve_user_input_to_hex

        params = {k: w.get().strip() for k, w in self.fields.items()}

        addr_text = self.addr_combo.get().strip()
        excel_map = load_location_excel_mapping(
            self.fields.get("location_excel_file").get().strip())
        raw = resolve_user_input_to_hex(addr_text, excel_map)
        if not raw or len(raw) % 2 != 0:
            messagebox.showerror("Error", "Invalid ATCS address or location name.")
            return

        try:
            addr_bytes = bytes.fromhex(raw)
        except Exception:
            messagebox.showerror("Error", "Invalid target address.")
            return

        start_time = self.start_time_entry.get().strip()
        end_time = self.end_time_entry.get().strip()
        suffix = self.suffix_entry.get().strip() or getattr(self, "profile_suffix", "")

        dlg = ProgressDialog(self, title="Running Analysis",
                             message="Processing logs...")

        def worker():
            out_path, err = None, None
            try:
                out_path = analyze_logs(
                    params.get("ixl_file") or False,
                    params.get("cm_log_file") or False,
                    params.get("pcap_file"),
                    params.get("ixl_excel_file") or False,
                    start_time,
                    end_time,
                    params.get("packetswitch_file") or "",
                    addr_bytes,
                    suffix,
                )
            except Exception as e:
                err = str(e)

            def done():
                dlg.destroy()
                if err:
                    messagebox.showerror("Error", f"Analysis failed:\n{err}")
                    return
                if not out_path:
                    messagebox.showwarning(
                        "Analysis", "The analysis did not produce an output file.")
                    return
                self.controller.show_results(out_path)

            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()
