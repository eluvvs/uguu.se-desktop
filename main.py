import flet as ft
from flet import FilePicker
import flet.file_picker # Force builder to see the submodule
import urllib.request
import urllib.error
import json
import os
import io
import threading
import mimetypes

# ── Constants ──────────────────────────────────────────────────────────────────
UPLOAD_URL = "https://uguu.se/upload"
MAX_FILE_SIZE = 128 * 1024 * 1024  # 128 MiB

# ── Colors ─────────────────────────────────────────────────────────────────────
BG = "#000000"
BG_SECONDARY = "#0a0a0a"
BG_CARD = "#111111"
ACCENT = "#5eaaff"
ACCENT_HOVER = "#7ec4ff"
TEXT = "#e8e8e8"
TEXT_DIM = "#707070"
TEXT_SUCCESS = "#6ddb8a"
TEXT_ERROR = "#ff6b81"
BORDER = "#1e1e1e"

def format_size(size_bytes):
    for unit in ("B", "KB", "MB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} GB"

class MultipartFormData:
    def __init__(self):
        self.boundary = "----UguuAndroid" + os.urandom(16).hex()
        self.parts = []

    def add_file(self, field_name, filepath, filename=None):
        if filename is None:
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

class ProgressReader(io.IOBase):
    def __init__(self, data, callback=None):
        self._stream = io.BytesIO(data)
        self.total = len(data)
        self.callback = callback

    def read(self, size=-1):
        chunk = self._stream.read(size)
        if self.callback and chunk:
            self.callback(self._stream.tell(), self.total)
        return chunk

    def __len__(self):
        return self.total

    def readinto(self, b):
        data = self.read(len(b))
        n = len(data)
        b[:n] = data
        return n

    def seekable(self): return False
    def readable(self): return True

def main(page: ft.Page):
    page.title = "Uguu Mobile"
    page.bgcolor = BG
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    
    # State
    files_state = []
    is_uploading = False

    # UI Components references
    files_column = ft.Column(spacing=10, scroll=ft.ScrollMode.HIDDEN)
    
    def on_file_picker_result(e):
        if e.files and not is_uploading:
            for f in e.files:
                # Avoid duplicates
                if not any(state_f["path"] == f.path for state_f in files_state):
                    files_state.append({
                        "path": f.path,
                        "name": f.name,
                        "size": f.size,
                        "status": "pending",
                        "url": None,
                        "error": None,
                    })
            refresh_file_list()



    # Header
    header = ft.Row([
        ft.Text("Uguu~", size=32, weight=ft.FontWeight.BOLD, color=ACCENT),
        ft.Text("Mobile file hosting", size=14, color=TEXT_DIM)
    ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.END)

    info_text = ft.Text("Max 128 MiB per file · Files expire after 3 hours", size=12, color=TEXT_DIM)

    # Empty placeholder
    placeholder = ft.Container(
        content=ft.Column([
            ft.Icon(ft.Icons.CLOUD_UPLOAD_OUTLINED, size=48, color=TEXT_DIM),
            ft.Text("No files selected\nTap 'Add Files' to begin", 
                   text_align=ft.TextAlign.CENTER, color=TEXT_DIM, size=14)
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        alignment=ft.Alignment(0, 0),
        expand=True,
    )

    list_container = ft.Container(
        content=placeholder,
        bgcolor=BG_CARD,
        border_radius=12,
        border=ft.border.all(2, BORDER),
        padding=10,
        expand=True,
        animate=ft.Animation(300, "decelerate")
    )

    status_text = ft.Text("Ready", size=12, color=TEXT_DIM)
    progress_bar = ft.ProgressBar(value=0, color=ACCENT, bgcolor=BG_CARD, visible=False)
    progress_text = ft.Text("0%", size=12, color=ACCENT, weight=ft.FontWeight.BOLD, visible=False)
    progress_row = ft.Row([progress_bar, progress_text], visible=False)

    def remove_file(index):
        if not is_uploading and 0 <= index < len(files_state):
            files_state.pop(index)
            refresh_file_list()

    def copy_url(url):
        page.set_clipboard(url)
        sb = ft.SnackBar(ft.Text(f"Copied: {url}"), bgcolor=ACCENT, duration=2000)
        page.overlay.append(sb)
        sb.open = True
        page.update()

    def refresh_file_list():
        if not files_state:
            list_container.content = placeholder
        else:
            rows = []
            for i, f in enumerate(files_state):
                # Status elements
                status_element = None
                if f["status"] == "done" and f["url"]:
                    status_element = ft.TextButton(
                        text=f["url"], 
                        on_click=lambda e, u=f["url"]: copy_url(u),
                        style=ft.ButtonStyle(color=TEXT_SUCCESS)
                    )
                elif f["status"] == "error":
                    err_txt = f["error"] or "Upload failed"
                    status_element = ft.Text(err_txt[:30] + ("..." if len(err_txt)>30 else ""), color=TEXT_ERROR, size=12)
                elif f["status"] == "uploading":
                    status_element = ft.Text("Uploading...", color=ACCENT, size=12)
                elif f["size"] > MAX_FILE_SIZE:
                    status_element = ft.Text("Too large!", color=TEXT_ERROR, size=12)

                # Delete button
                del_btn = ft.IconButton(
                    icon=ft.Icons.CLOSE, 
                    icon_color=TEXT_DIM,
                    icon_size=18,
                    on_click=lambda e, idx=i: remove_file(idx),
                    visible=not is_uploading
                )

                # File Row content
                row_content = ft.Row([
                    ft.Column([
                        ft.Text(f["name"][:30] + ("..." if len(f["name"])>30 else ""), size=14, color=TEXT),
                        ft.Text(format_size(f["size"]), size=12, color=TEXT_DIM)
                    ], expand=True),
                    status_element if status_element else ft.Container(),
                    del_btn
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

                # Animating row entrance
                row_container = ft.Container(
                    content=row_content,
                    bgcolor=BG_SECONDARY if i % 2 == 0 else BG_CARD,
                    border_radius=8,
                    padding=10,
                    animate=ft.Animation(400, "bounceOut"),
                    offset=ft.Offset(0, 0),
                    opacity=1
                )
                rows.append(row_container)

            files_column.controls = rows
            list_container.content = files_column
        
        page.update()

    def clear_files(e):
        if not is_uploading:
            files_state.clear()
            refresh_file_list()
            status_text.value = "Ready"
            page.update()

    import asyncio
    async def add_files(e):
        if not is_uploading:
            # We use the existing picker or create one if it doesn't exist
            picker = None
            for control in page.overlay:
                if isinstance(control, ft.FilePicker):
                    picker = control
                    break
            
            if not picker:
                picker = ft.FilePicker()
                picker.on_result = on_file_picker_result
                page.overlay.append(picker)
                page.update()
                # Wait for the mobile client to register the control
                await asyncio.sleep(0.3)
            
            picker.pick_files(allow_multiple=True)

    def start_upload(e):
        nonlocal is_uploading
        if is_uploading:
            return

        pending = [f for f in files_state if f["status"] == "pending" and f["size"] <= MAX_FILE_SIZE]
        if not pending:
            status_text.value = "No valid files to upload"
            page.update()
            return

        is_uploading = True
        add_btn.disabled = True
        clear_btn.disabled = True
        upload_btn.disabled = True
        upload_btn.bgcolor = BORDER
        
        status_text.value = f"Uploading {len(pending)} file(s)..."
        progress_bar.value = 0
        progress_text.value = "0%"
        progress_row.visible = True
        refresh_file_list()

        threading.Thread(target=upload_worker, args=(pending,), daemon=True).start()

    def upload_worker(pending):
        nonlocal is_uploading
        done_count = 0
        error_count = 0

        try:
            for f in pending:
                f["status"] = "uploading"
                page.update()

                try:
                    form = MultipartFormData()
                    form.add_file("files[]", f["path"], f["name"])
                    body = form.encode()

                    file_idx = pending.index(f)
                    total_files = len(pending)

                    def on_progress(sent, total, _fi=file_idx, _tf=total_files):
                        overall_pct = ((_fi + sent / total) / _tf) if total else 0
                        progress_bar.value = overall_pct
                        progress_text.value = f"{int(overall_pct * 100)}%"
                        page.update()

                    reader = ProgressReader(body, callback=on_progress)

                    req = urllib.request.Request(
                        UPLOAD_URL,
                        data=reader,
                        headers={
                            "Content-Type": form.content_type,
                            "Content-Length": str(len(body)),
                            "User-Agent": "UguuMobile/1.0",
                        },
                        method="POST",
                    )

                    with urllib.request.urlopen(req, timeout=120) as resp:
                        response_data = resp.read().decode("utf-8")

                    try:
                        result = json.loads(response_data)
                    except json.JSONDecodeError:
                        url_candidate = response_data.strip()
                        if url_candidate.startswith("http"):
                            f["url"] = url_candidate
                            f["status"] = "done"
                            done_count += 1
                            continue
                        else:
                            f["status"] = "error"
                            f["error"] = "Bad response"
                            error_count += 1
                            continue

                    if isinstance(result, dict) and result.get("success"):
                        files_list = result.get("files", [])
                        if files_list and files_list[0].get("url"):
                            f["url"] = files_list[0]["url"]
                            f["status"] = "done"
                            done_count += 1
                        else:
                            f["status"] = "error"
                            f["error"] = "No URL in response"
                            error_count += 1
                    else:
                        f["status"] = "error"
                        f["error"] = result.get("description", "Upload rejected") if isinstance(result, dict) else "Unexpected format"
                        error_count += 1

                except Exception as e:
                    f["status"] = "error"
                    f["error"] = str(e)
                    error_count += 1

                page.update()

        except Exception as e:
            status_text.value = f"Fatal upload error"

        is_uploading = False
        status_msg = f"Done! {done_count} uploaded"
        if error_count:
            status_msg += f", {error_count} failed"
        
        status_text.value = status_msg
        
        # Reset buttons and progress
        add_btn.disabled = False
        clear_btn.disabled = False
        upload_btn.disabled = False
        upload_btn.bgcolor = ACCENT
        progress_bar.value = 1.0
        progress_text.value = "100%"
        
        page.update()

        import time
        time.sleep(1)
        progress_row.visible = False
        refresh_file_list()
        page.update()


    # Buttons
    add_btn = ft.ElevatedButton(
        "＋ Add Files", 
        color=TEXT, 
        bgcolor=BG_SECONDARY, 
        on_click=add_files,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
    )
    
    clear_btn = ft.ElevatedButton(
        "✕ Clear", 
        color=TEXT_DIM, 
        bgcolor=BG_SECONDARY, 
        on_click=clear_files,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
    )
    
    upload_btn = ft.ElevatedButton(
        "Upload", 
        color=BG, 
        bgcolor=ACCENT, 
        on_click=start_upload,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), padding=20)
    )

    buttons_row = ft.Row([
        add_btn,
        clear_btn,
        ft.Container(expand=True),
        upload_btn
    ])

    page.add(
        header,
        info_text,
        list_container,
        progress_row,
        buttons_row,
        status_text
    )

def safe_main(page: ft.Page):
    try:
        main(page)
    except Exception as e:
        import traceback
        page.clean()
        page.scroll = ft.ScrollMode.AUTO
        page.add(ft.Text(f"CRASH: {e}\n{traceback.format_exc()}", color="red", selectable=True))
        page.update()

if __name__ == "__main__":
    ft.app(target=safe_main)
