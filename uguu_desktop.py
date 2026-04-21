"""
Uguu Desktop — Lightweight file uploader for uguu.se
Upload files and get temporary shareable links.
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, ttk
import urllib.request
import urllib.error
import json
import mimetypes


# ── Constants ──────────────────────────────────────────────────────────────────
UPLOAD_URL = "https://uguu.se/upload"
MAX_FILE_SIZE = 128 * 1024 * 1024  # 128 MiB
APP_TITLE = "Uguu Desktop"
WINDOW_WIDTH = 520
WINDOW_HEIGHT = 480


# ── Colors ─────────────────────────────────────────────────────────────────────
BG = "#1e1e2e"
BG_SECONDARY = "#282840"
BG_CARD = "#313152"
ACCENT = "#89b4fa"
ACCENT_HOVER = "#74c7ec"
TEXT = "#cdd6f4"
TEXT_DIM = "#6c7086"
TEXT_SUCCESS = "#a6e3a1"
TEXT_ERROR = "#f38ba8"
BORDER = "#45475a"


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)


def format_size(size_bytes):
    """Format bytes into human-readable string."""
    for unit in ("B", "KB", "MB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} GB"


class MultipartFormData:
    """Build a multipart/form-data body using only stdlib."""

    def __init__(self):
        self.boundary = "----UguuDesktop" + os.urandom(16).hex()
        self.parts = []

    def add_file(self, field_name, filepath):
        filename = os.path.basename(filepath)
        mime_type = mimetypes.guess_type(filepath)[0] or "application/octet-stream"
        with open(filepath, "rb") as f:
            data = f.read()
        self.parts.append((field_name, filename, mime_type, data))

    def encode(self):
        lines = []
        for field_name, filename, mime_type, data in self.parts:
            lines.append(f"--{self.boundary}".encode())
            lines.append(
                f'Content-Disposition: form-data; name="{field_name}"; '
                f'filename="{filename}"'.encode()
            )
            lines.append(f"Content-Type: {mime_type}".encode())
            lines.append(b"")
            lines.append(data)
        lines.append(f"--{self.boundary}--".encode())
        lines.append(b"")
        return b"\r\n".join(lines)

    @property
    def content_type(self):
        return f"multipart/form-data; boundary={self.boundary}"


class UguuDesktop:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.minsize(420, 380)
        self.root.configure(bg=BG)
        self.root.resizable(True, True)

        # Try to set icon
        icon_path = resource_path("icon.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except tk.TclError:
                pass

        self.files = []
        self.uploading = False

        self._build_ui()

    def _build_ui(self):
        # ── Main container ─────────────────────────────────────────────────
        main = tk.Frame(self.root, bg=BG)
        main.pack(fill="both", expand=True, padx=20, pady=16)

        # ── Header ─────────────────────────────────────────────────────────
        header = tk.Frame(main, bg=BG)
        header.pack(fill="x", pady=(0, 4))

        title_label = tk.Label(
            header, text="Uguu~", font=("Segoe UI", 22, "bold"),
            fg=ACCENT, bg=BG
        )
        title_label.pack(side="left")

        subtitle = tk.Label(
            header, text="Temporary file hosting",
            font=("Segoe UI", 10), fg=TEXT_DIM, bg=BG
        )
        subtitle.pack(side="left", padx=(10, 0), pady=(8, 0))

        info_label = tk.Label(
            main,
            text="Max 128 MiB per file  ·  Files expire after 3 hours",
            font=("Segoe UI", 9), fg=TEXT_DIM, bg=BG
        )
        info_label.pack(anchor="w", pady=(0, 10))

        # ── File list area ─────────────────────────────────────────────────
        list_frame = tk.Frame(main, bg=BG_CARD, highlightbackground=BORDER,
                              highlightthickness=1)
        list_frame.pack(fill="both", expand=True, pady=(0, 10))

        # Scrollable file list
        self.canvas = tk.Canvas(list_frame, bg=BG_CARD, highlightthickness=0,
                                borderwidth=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical",
                                  command=self.canvas.yview)

        self.file_list_frame = tk.Frame(self.canvas, bg=BG_CARD)
        self.file_list_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.file_list_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Placeholder text
        self.placeholder = tk.Label(
            self.file_list_frame,
            text="No files selected\nClick 'Add Files' to get started",
            font=("Segoe UI", 11), fg=TEXT_DIM, bg=BG_CARD,
            justify="center"
        )
        self.placeholder.pack(expand=True, fill="both", pady=40)

        # Bind mousewheel
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # ── Buttons ────────────────────────────────────────────────────────
        btn_frame = tk.Frame(main, bg=BG)
        btn_frame.pack(fill="x", pady=(0, 6))

        self.add_btn = tk.Button(
            btn_frame, text="＋ Add Files", font=("Segoe UI", 10),
            fg=TEXT, bg=BG_SECONDARY, activebackground=BG_CARD,
            activeforeground=TEXT, relief="flat", cursor="hand2",
            padx=16, pady=6, command=self._add_files
        )
        self.add_btn.pack(side="left")

        self.clear_btn = tk.Button(
            btn_frame, text="✕ Clear", font=("Segoe UI", 10),
            fg=TEXT_DIM, bg=BG_SECONDARY, activebackground=BG_CARD,
            activeforeground=TEXT, relief="flat", cursor="hand2",
            padx=16, pady=6, command=self._clear_files
        )
        self.clear_btn.pack(side="left", padx=(8, 0))

        self.upload_btn = tk.Button(
            btn_frame, text="Upload", font=("Segoe UI", 10, "bold"),
            fg=BG, bg=ACCENT, activebackground=ACCENT_HOVER,
            activeforeground=BG, relief="flat", cursor="hand2",
            padx=24, pady=6, command=self._start_upload
        )
        self.upload_btn.pack(side="right")

        # ── Status bar ─────────────────────────────────────────────────────
        self.status_var = tk.StringVar(value="Ready")
        status_bar = tk.Label(
            main, textvariable=self.status_var, font=("Segoe UI", 9),
            fg=TEXT_DIM, bg=BG, anchor="w"
        )
        status_bar.pack(fill="x")

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _add_files(self):
        if self.uploading:
            return
        paths = filedialog.askopenfilenames(
            title="Select files to upload",
            filetypes=[("All files", "*.*")]
        )
        if not paths:
            return

        for path in paths:
            if path in [f["path"] for f in self.files]:
                continue
            size = os.path.getsize(path)
            self.files.append({
                "path": path,
                "name": os.path.basename(path),
                "size": size,
                "status": "pending",  # pending, uploading, done, error
                "url": None,
                "error": None,
            })

        self._refresh_file_list()

    def _clear_files(self):
        if self.uploading:
            return
        self.files.clear()
        self._refresh_file_list()
        self.status_var.set("Ready")

    def _refresh_file_list(self):
        for widget in self.file_list_frame.winfo_children():
            widget.destroy()

        if not self.files:
            self.placeholder = tk.Label(
                self.file_list_frame,
                text="No files selected\nClick 'Add Files' to get started",
                font=("Segoe UI", 11), fg=TEXT_DIM, bg=BG_CARD,
                justify="center"
            )
            self.placeholder.pack(expand=True, fill="both", pady=40)
            return

        for i, f in enumerate(self.files):
            row_bg = BG_CARD if i % 2 == 0 else BG_SECONDARY
            row = tk.Frame(self.file_list_frame, bg=row_bg)
            row.pack(fill="x", padx=6, pady=2)

            # File name + size
            name_text = f["name"]
            if len(name_text) > 35:
                name_text = name_text[:32] + "..."
            name_label = tk.Label(
                row, text=name_text, font=("Segoe UI", 10),
                fg=TEXT, bg=row_bg, anchor="w"
            )
            name_label.pack(side="left", padx=(8, 4), pady=4)

            size_label = tk.Label(
                row, text=format_size(f["size"]),
                font=("Segoe UI", 9), fg=TEXT_DIM, bg=row_bg
            )
            size_label.pack(side="left", padx=(0, 8), pady=4)

            # Status / link
            if f["status"] == "done" and f["url"]:
                link_btn = tk.Button(
                    row, text=f["url"], font=("Segoe UI", 9, "underline"),
                    fg=TEXT_SUCCESS, bg=row_bg, activebackground=row_bg,
                    activeforeground=ACCENT_HOVER, relief="flat",
                    cursor="hand2",
                    command=lambda url=f["url"]: self._copy_to_clipboard(url)
                )
                link_btn.pack(side="right", padx=(0, 8), pady=4)
            elif f["status"] == "error":
                err_text = f["error"] or "Upload failed"
                if len(err_text) > 30:
                    err_text = err_text[:27] + "..."
                err_label = tk.Label(
                    row, text=err_text, font=("Segoe UI", 9),
                    fg=TEXT_ERROR, bg=row_bg
                )
                err_label.pack(side="right", padx=(0, 8), pady=4)
            elif f["status"] == "uploading":
                up_label = tk.Label(
                    row, text="Uploading...", font=("Segoe UI", 9),
                    fg=ACCENT, bg=row_bg
                )
                up_label.pack(side="right", padx=(0, 8), pady=4)
            elif f["size"] > MAX_FILE_SIZE:
                warn_label = tk.Label(
                    row, text="Too large!", font=("Segoe UI", 9),
                    fg=TEXT_ERROR, bg=row_bg
                )
                warn_label.pack(side="right", padx=(0, 8), pady=4)

            # Remove button (only when not uploading)
            if not self.uploading:
                idx = i
                rm_btn = tk.Button(
                    row, text="✕", font=("Segoe UI", 9),
                    fg=TEXT_DIM, bg=row_bg, activebackground=row_bg,
                    activeforeground=TEXT_ERROR, relief="flat",
                    cursor="hand2", width=2,
                    command=lambda idx=idx: self._remove_file(idx)
                )
                rm_btn.pack(side="right", pady=4)

        # Force canvas scroll region update
        self.file_list_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _remove_file(self, index):
        if 0 <= index < len(self.files):
            self.files.pop(index)
            self._refresh_file_list()

    def _copy_to_clipboard(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status_var.set(f"Copied: {text}")

    def _start_upload(self):
        if self.uploading:
            return

        pending = [f for f in self.files
                   if f["status"] == "pending" and f["size"] <= MAX_FILE_SIZE]
        if not pending:
            self.status_var.set("No valid files to upload")
            return

        self.uploading = True
        self.upload_btn.configure(state="disabled", bg=BORDER)
        self.add_btn.configure(state="disabled")
        self.clear_btn.configure(state="disabled")
        self.status_var.set(f"Uploading {len(pending)} file(s)...")

        thread = threading.Thread(target=self._upload_files, args=(pending,),
                                  daemon=True)
        thread.start()

    def _upload_files(self, pending):
        """Upload files one by one (each as a separate request for reliability)."""
        done_count = 0
        error_count = 0

        for f in pending:
            f["status"] = "uploading"
            self.root.after(0, self._refresh_file_list)

            try:
                if f["size"] > MAX_FILE_SIZE:
                    raise ValueError("File exceeds 128 MiB limit")

                form = MultipartFormData()
                form.add_file("files[]", f["path"])
                body = form.encode()

                req = urllib.request.Request(
                    UPLOAD_URL,
                    data=body,
                    headers={
                        "Content-Type": form.content_type,
                        "User-Agent": "UguuDesktop/1.0",
                    },
                    method="POST",
                )

                with urllib.request.urlopen(req, timeout=120) as resp:
                    response_data = resp.read().decode("utf-8")
                    result = json.loads(response_data)

                # Response is a list of objects with "url" key
                if isinstance(result, list) and len(result) > 0:
                    url = result[0].get("url", "")
                    if url:
                        f["url"] = url
                        f["status"] = "done"
                        done_count += 1
                    else:
                        f["status"] = "error"
                        f["error"] = "No URL in response"
                        error_count += 1
                else:
                    f["status"] = "error"
                    f["error"] = "Unexpected response format"
                    error_count += 1

            except urllib.error.HTTPError as e:
                f["status"] = "error"
                f["error"] = f"HTTP {e.code}: {e.reason}"
                error_count += 1
            except urllib.error.URLError as e:
                f["status"] = "error"
                f["error"] = f"Connection error: {e.reason}"
                error_count += 1
            except Exception as e:
                f["status"] = "error"
                f["error"] = str(e)
                error_count += 1

            self.root.after(0, self._refresh_file_list)

        # Done
        status_msg = f"Done! {done_count} uploaded"
        if error_count:
            status_msg += f", {error_count} failed"
        status_msg += "  ·  Click a link to copy"

        def _finish():
            self.uploading = False
            self.upload_btn.configure(state="normal", bg=ACCENT)
            self.add_btn.configure(state="normal")
            self.clear_btn.configure(state="normal")
            self.status_var.set(status_msg)
            self._refresh_file_list()

        self.root.after(0, _finish)


def main():
    root = tk.Tk()

    # Apply a dark ttk theme for scrollbar
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Vertical.TScrollbar",
                     background=BG_SECONDARY,
                     troughcolor=BG_CARD,
                     arrowcolor=TEXT_DIM,
                     borderwidth=0)

    app = UguuDesktop(root)
    root.mainloop()


if __name__ == "__main__":
    main()
