import io
import os
import shutil
import subprocess
import textwrap
import tkinter as tk
from tkinter import colorchooser, messagebox
from PIL import Image, ImageDraw, ImageFont, ImageTk
MAX_WIDTH = 40
drag_target = None
handle_radius = 14
preview_display_w = 700
preview_display_h = 450
APP_DIR = os.path.dirname(os.path.abspath(__file__))
background_image = None
original_w, original_h = 1, 1
quote_pos = [150, 200]
author_pos = [200, 300]
quote_color = "white"
author_color = "white"
quote_outline_color = "black"
author_outline_color = "black"
quote_outline_width = 2
author_outline_width = 2
OPEN_QUOTE_SYMBOL = "“"
CLOSE_QUOTE_SYMBOL = "”"
FONT_PATH_CANDIDATES = {
    "Times New Roman": {
        "regular": [
            r"C:\Windows\Fonts\times.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf",
        ],
        "bold": [
            r"C:\Windows\Fonts\timesbd.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf",
        ],
        "italic": [
            r"C:\Windows\Fonts\timesi.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSerif-Italic.ttf",
        ],
    },
    "Calibri": {
        "regular": [
            r"C:\Windows\Fonts\calibri.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        ],
        "bold": [
            r"C:\Windows\Fonts\calibrib.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        ],
        "italic": [
            r"C:\Windows\Fonts\calibrii.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Italic.ttf",
        ],
    },
}
def get_font(name, size, style="regular"):
    family = FONT_PATH_CANDIDATES.get(name, {})
    candidates = family.get(style, []) + family.get("regular", [])
    for font_path in candidates:
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            continue
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()
def normalize_input_text(text):
    return text.replace("\\n", "\n")
def wrap_text(text):
    text = normalize_input_text(text)
    paragraphs = text.split("\n")
    wrapped_lines = []
    for paragraph in paragraphs:
        if paragraph.strip() == "":
            wrapped_lines.append("")
            continue
        wrapped_lines.extend(textwrap.wrap(paragraph, width=MAX_WIDTH))
    return "\n".join(wrapped_lines)
def build_author_text(author):
    return f"- {wrap_text(author)} -"
def format_quote_text(text):
    wrapped = wrap_text(text).strip()
    if not wrapped:
        return f"{OPEN_QUOTE_SYMBOL}{CLOSE_QUOTE_SYMBOL}"
    lines = wrapped.split("\n")
    lines[0] = f"{OPEN_QUOTE_SYMBOL} {lines[0]}"
    lines[-1] = f"{lines[-1]} {CLOSE_QUOTE_SYMBOL}"
    return "\n".join(lines)
def parse_inline_styles(line):
    runs, i = [], 0
    while i < len(line):
        bold_start = line.find("**", i)
        italic_start = line.find("__", i)
        markers = [idx for idx in (bold_start, italic_start) if idx != -1]
        if not markers:
            if i < len(line):
                runs.append((line[i:], "regular"))
            break
        start = min(markers)
        if start > i:
            runs.append((line[i:start], "regular"))
        marker = "**" if bold_start == start else "__"
        style = "bold" if marker == "**" else "italic"
        end = line.find(marker, start + 2)
        if end == -1:
            runs.append((line[start:], "regular"))
            break
        content = line[start + 2:end]
        if content:
            runs.append((content, style))
        i = end + 2
    return runs
def get_line_height(font_name, font_size):
    font = get_font(font_name, font_size, "regular")
    box = font.getbbox("Ag")
    return box[3] - box[1] + max(4, font_size // 8)
def draw_segment_with_outline(draw, x, y, text, font, fill, out_w, out_color):
    for dx in range(-out_w, out_w + 1):
        for dy in range(-out_w, out_w + 1):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), text, font=font, fill=out_color)
    draw.text((x, y), text, font=font, fill=fill)
def draw_formatted_text_with_outline(draw, pos, text, font_name, font_size, fill, out_w, out_color):
    x, y = pos
    line_height = get_line_height(font_name, font_size)
    for line_idx, line in enumerate(text.split("\n")):
        cursor_x = x
        cursor_y = y + line_idx * line_height
        runs = parse_inline_styles(line)
        for segment, style in runs:
            if not segment:
                continue
            font = get_font(font_name, font_size, style)
            draw_segment_with_outline(draw, cursor_x, cursor_y, segment, font, fill, out_w, out_color)
            seg_box = font.getbbox(segment)
            cursor_x += seg_box[2] - seg_box[0]
def draw_handle(draw, center, fill, icon_color="white"):
    cx, cy = center
    r = handle_radius
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=fill)
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline="white", width=2)
    plus_half = max(4, r // 2)
    line_w = 3
    draw.line([cx - plus_half, cy, cx + plus_half, cy], fill=icon_color, width=line_w)
    draw.line([cx, cy - plus_half, cx, cy + plus_half], fill=icon_color, width=line_w)
def point_in_handle(point_x, point_y, center_x, center_y):
    dx = point_x - center_x
    dy = point_y - center_y
    return (dx * dx + dy * dy) <= (handle_radius * handle_radius)
def require_background_loaded(show_message=True):
    if background_image is None:
        if show_message:
            messagebox.showwarning("Missing background", "Vui lòng load background trước khi thao tác.")
        return False
    return True
def load_background():
    global background_image, original_w, original_h
    bg_name = bg_name_var.get().strip()
    if not bg_name:
        messagebox.showwarning("Missing background name", "Vui lòng nhập tên file background (ví dụ: background.jpg).")
        return
    bg_path = os.path.join(APP_DIR, bg_name)
    if not os.path.isfile(bg_path):
        messagebox.showerror("Background not found", f"Không tìm thấy file:\n{bg_path}")
        return
    try:
        background_image = Image.open(bg_path).convert("RGBA")
    except Exception as exc:
        messagebox.showerror("Load failed", f"Không thể load background:\n{exc}")
        return
    original_w, original_h = background_image.size
    update_preview()
def render_canvas_image(show_handles=True):
    if background_image is None:
        return None
    quote = quote_entry.get()
    author = author_entry.get()
    img = background_image.copy()
    draw = ImageDraw.Draw(img)
    draw_formatted_text_with_outline(
        draw, tuple(quote_pos), format_quote_text(quote),
        quote_font_var.get(), quote_size.get(), quote_color,
        quote_outline_width, quote_outline_color,
    )
    draw_formatted_text_with_outline(
        draw, tuple(author_pos), build_author_text(author),
        author_font_var.get(), author_size.get(), author_color,
        author_outline_width, author_outline_color,
    )
    if show_handles:
        draw_handle(draw, tuple(quote_pos), fill="#ff5a5f")
        draw_handle(draw, tuple(author_pos), fill="#1f8ef1")
    return img
def fit_image_to_box(img, box_w, box_h):
    if box_w <= 1 or box_h <= 1:
        return img.copy()
    ratio = min(box_w / img.width, box_h / img.height)
    new_w = max(1, int(img.width * ratio))
    new_h = max(1, int(img.height * ratio))
    return img.resize((new_w, new_h), Image.Resampling.LANCZOS)
def clamp_position(x, y):
    if background_image is None:
        return x, y
    x = min(max(0, x), max(0, original_w - 1))
    y = min(max(0, y), max(0, original_h - 1))
    return x, y
def update_coordinate_inputs():
    if "quote_x_var" not in globals() or "author_x_var" not in globals():
        return
    quote_x_var.set(str(quote_pos[0]))
    quote_y_var.set(str(quote_pos[1]))
    author_x_var.set(str(author_pos[0]))
    author_y_var.set(str(author_pos[1]))
def update_preview(*args):
    global preview_img, final_image, preview_display_w, preview_display_h
    update_coordinate_inputs()
    if background_image is None:
        final_image = None
        preview_img = None
        preview_label.config(image="", text="Load background trước khi edit :>", fg="white", bg="#1f2430", font=("Arial", 16, "bold"))
        return
    final_image = render_canvas_image(show_handles=False)
    preview_image = render_canvas_image(show_handles=True)
    panel_w = max(10, right.winfo_width() - 20)
    panel_h = max(10, right.winfo_height() - 20)
    fitted = fit_image_to_box(preview_image, panel_w, panel_h)
    preview_display_w, preview_display_h = fitted.size
    preview_img = ImageTk.PhotoImage(fitted)
    preview_label.config(image=preview_img, text="")
def save_image():
    if not require_background_loaded(show_message=True):
        return
    filename = save_name_var.get().strip()
    if not filename:
        messagebox.showwarning("Missing file name", "Vui lòng nhập tên file trước khi lưu.")
        return
    ext = save_format_var.get().lower().strip(".")
    if ext not in ("png", "jpg"):
        ext = "png"
    safe_name = "".join(ch for ch in filename if ch not in '\\/:*?"<>|').strip()
    if not safe_name:
        messagebox.showwarning("Invalid file name", "Tên file không hợp lệ.")
        return
    app_dir = os.path.dirname(os.path.abspath(__file__))
    save_path = os.path.join(app_dir, f"{safe_name}.{ext}")
    clean_image = render_canvas_image(show_handles=False)
    if ext == "jpg":
        clean_image = clean_image.convert("RGB")
    clean_image.save(save_path)
    messagebox.showinfo("Saved", f"Đã lưu ảnh tại:\n{save_path}")
def copy_image_to_clipboard():
    if not require_background_loaded(show_message=True):
        return
    image = render_canvas_image(show_handles=False)
    if os.name == "nt":
        try:
            from ctypes import wintypes
            import ctypes
            output = io.BytesIO()
            image.convert("RGB").save(output, "BMP")
            data = output.getvalue()[14:]
            output.close()
            GMEM_MOVEABLE = 0x0002
            CF_DIB = 8
            kernel32 = ctypes.windll.kernel32
            user32 = ctypes.windll.user32
            h_global = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
            p_global = kernel32.GlobalLock(h_global)
            ctypes.memmove(p_global, data, len(data))
            kernel32.GlobalUnlock(h_global)
            user32.OpenClipboard(0)
            user32.EmptyClipboard()
            user32.SetClipboardData(CF_DIB, h_global)
            user32.CloseClipboard()
            messagebox.showinfo("Copied", "Đã copy ảnh vào clipboard.")
            return
        except Exception:
            pass
    if shutil.which("xclip"):
        try:
            output = io.BytesIO()
            image.save(output, format="PNG")
            subprocess.run(
                ["xclip", "-selection", "clipboard", "-t", "image/png", "-i"],
                input=output.getvalue(),
                check=True,
            )
            messagebox.showinfo("Copied", "Đã copy ảnh vào clipboard.")
            return
        except Exception:
            pass
    messagebox.showwarning(
        "Clipboard unsupported",
        "Không copy trực tiếp ảnh được trên môi trường này. Hãy dùng Save Image rồi copy file ảnh.",
    )
def start_drag(event):
    global drag_target
    if not require_background_loaded(show_message=True):
        drag_target = None
        return
    scale_x = original_w / max(1, preview_display_w)
    scale_y = original_h / max(1, preview_display_h)
    mx = int(event.x * scale_x)
    my = int(event.y * scale_y)
    if point_in_handle(mx, my, quote_pos[0], quote_pos[1]):
        drag_target = "quote"
    elif point_in_handle(mx, my, author_pos[0], author_pos[1]):
        drag_target = "author"
    else:
        drag_target = None
def drag(event):
    global drag_target
    if not drag_target or not require_background_loaded(show_message=False):
        return
    scale_x = original_w / max(1, preview_display_w)
    scale_y = original_h / max(1, preview_display_h)
    if drag_target == "quote":
        quote_pos[0] = int(event.x * scale_x)
        quote_pos[1] = int(event.y * scale_y)
        quote_pos[0], quote_pos[1] = clamp_position(quote_pos[0], quote_pos[1])
    else:
        author_pos[0] = int(event.x * scale_x)
        author_pos[1] = int(event.y * scale_y)
        author_pos[0], author_pos[1] = clamp_position(author_pos[0], author_pos[1])
    update_preview()
def stop_drag(event):
    global drag_target
    drag_target = None
def apply_quote_position(event=None):
    try:
        x = int(quote_x_var.get().strip())
        y = int(quote_y_var.get().strip())
    except ValueError:
        messagebox.showwarning("Invalid quote position", "Tọa độ quote phải là số nguyên.")
        update_coordinate_inputs()
        return
    x, y = clamp_position(x, y)
    quote_pos[0], quote_pos[1] = x, y
    update_preview()
def apply_author_position(event=None):
    try:
        x = int(author_x_var.get().strip())
        y = int(author_y_var.get().strip())
    except ValueError:
        messagebox.showwarning("Invalid author position", "Tọa độ author phải là số nguyên.")
        update_coordinate_inputs()
        return
    x, y = clamp_position(x, y)
    author_pos[0], author_pos[1] = x, y
    update_preview()
def choose_quote_color():
    global quote_color
    c = colorchooser.askcolor()[1]
    if c:
        quote_color = c
        update_preview()
def choose_author_color():
    global author_color
    c = colorchooser.askcolor()[1]
    if c:
        author_color = c
        update_preview()
def choose_quote_outline_color():
    global quote_outline_color
    c = colorchooser.askcolor()[1]
    if c:
        quote_outline_color = c
        update_preview()
def choose_author_outline_color():
    global author_outline_color
    c = colorchooser.askcolor()[1]
    if c:
        author_outline_color = c
        update_preview()
def update_quote_outline(val):
    global quote_outline_width
    quote_outline_width = int(val)
    update_preview()
def update_author_outline(val):
    global author_outline_width
    author_outline_width = int(val)
    update_preview()
def on_right_resize(event):
    update_preview()
def make_section_label(parent, text, pady=(6, 4)):
    tk.Label(parent, text=text, bg="#2a3142", fg="white", anchor="w").pack(fill="x", pady=pady)
root = tk.Tk()
root.title("FINAL QOUTE EDITOR -REALLY BY FOGOTTEN-")
root.geometry("1220x760")
root.minsize(980, 640)
root.configure(bg="#1f2430")
main = tk.PanedWindow(root, orient="horizontal", sashwidth=6, bg="#1f2430", bd=0)
main.pack(fill="both", expand=True)
left_container = tk.Frame(main, bg="#2a3142", width=360)
main.add(left_container, minsize=300)
right = tk.Frame(main, bg="#1f2430")
main.add(right)
left_canvas = tk.Canvas(left_container, bg="#2a3142", highlightthickness=0)
left_scroll = tk.Scrollbar(left_container, orient="vertical", command=left_canvas.yview)
left_canvas.configure(yscrollcommand=left_scroll.set)
left_scroll.pack(side="right", fill="y")
left_canvas.pack(side="left", fill="both", expand=True)
left = tk.Frame(left_canvas, bg="#2a3142", padx=12, pady=12)
left_window = left_canvas.create_window((0, 0), window=left, anchor="nw")
def on_left_configure(event):
    left_canvas.configure(scrollregion=left_canvas.bbox("all"))
def on_canvas_configure(event):
    left_canvas.itemconfig(left_window, width=event.width)
left.bind("<Configure>", on_left_configure)
left_canvas.bind("<Configure>", on_canvas_configure)
preview_label = tk.Label(right, bd=0, highlightthickness=0, bg="#1f2430")
preview_label.pack(expand=True)
right.bind("<Configure>", on_right_resize)
make_section_label(left, "Background", pady=(0, 4))
bg_name_var = tk.StringVar(value="background.jpg")
bg_name_entry = tk.Entry(left, textvariable=bg_name_var, width=34)
bg_name_entry.pack(fill="x", pady=(0, 8))
tk.Button(left, text="Load Background", command=load_background, bg="#f39c12", fg="white", relief="flat").pack(fill="x", pady=(0, 12))
make_section_label(left, "Quote", pady=(0, 4))
quote_entry = tk.Entry(left, width=34)
quote_entry.pack(fill="x", pady=(0, 10))
quote_entry.bind("<KeyRelease>", update_preview)
make_section_label(left, "Author", pady=(0, 4))
author_entry = tk.Entry(left, width=34)
author_entry.pack(fill="x", pady=(0, 10))
author_entry.bind("<KeyRelease>", update_preview)
quote_font_var = tk.StringVar(value="Times New Roman")
author_font_var = tk.StringVar(value="Times New Roman")
tk.OptionMenu(left, quote_font_var, "Times New Roman", "Calibri", command=update_preview).pack(fill="x")
quote_size = tk.Scale(left, from_=20, to=100, orient="horizontal", label="Quote Size", command=update_preview)
quote_size.set(40)
quote_size.pack(fill="x")
tk.Button(left, text="Quote Color", command=choose_quote_color).pack(fill="x", pady=(4, 10))
tk.OptionMenu(left, author_font_var, "Times New Roman", "Calibri", command=update_preview).pack(fill="x")
author_size = tk.Scale(left, from_=15, to=80, orient="horizontal", label="Author Size", command=update_preview)
author_size.set(30)
author_size.pack(fill="x")
tk.Button(left, text="Author Color", command=choose_author_color).pack(fill="x", pady=(4, 10))
make_section_label(left, "Tọa độ Qoute/Author", pady=(6, 2))
quote_x_var = tk.StringVar(value=str(quote_pos[0]))
quote_y_var = tk.StringVar(value=str(quote_pos[1]))
author_x_var = tk.StringVar(value=str(author_pos[0]))
author_y_var = tk.StringVar(value=str(author_pos[1]))
quote_pos_frame = tk.Frame(left, bg="#2a3142")
quote_pos_frame.pack(fill="x", pady=(0, 6))
tk.Label(quote_pos_frame, text="Quote X", bg="#2a3142", fg="white").grid(row=0, column=0, sticky="w")
quote_x_entry = tk.Entry(quote_pos_frame, textvariable=quote_x_var, width=8)
quote_x_entry.grid(row=0, column=1, padx=(6, 12))
tk.Label(quote_pos_frame, text="Y", bg="#2a3142", fg="white").grid(row=0, column=2, sticky="w")
quote_y_entry = tk.Entry(quote_pos_frame, textvariable=quote_y_var, width=8)
quote_y_entry.grid(row=0, column=3, padx=(6, 0))
tk.Button(quote_pos_frame, text="Áp dụng", command=apply_quote_position).grid(row=0, column=4, padx=(8, 0))
author_pos_frame = tk.Frame(left, bg="#2a3142")
author_pos_frame.pack(fill="x", pady=(0, 10))
tk.Label(author_pos_frame, text="Author X", bg="#2a3142", fg="white").grid(row=0, column=0, sticky="w")
author_x_entry = tk.Entry(author_pos_frame, textvariable=author_x_var, width=8)
author_x_entry.grid(row=0, column=1, padx=(6, 12))
tk.Label(author_pos_frame, text="Y", bg="#2a3142", fg="white").grid(row=0, column=2, sticky="w")
author_y_entry = tk.Entry(author_pos_frame, textvariable=author_y_var, width=8)
author_y_entry.grid(row=0, column=3, padx=(6, 0))
tk.Button(author_pos_frame, text="Áp dụng", command=apply_author_position).grid(row=0, column=4, padx=(8, 0))
make_section_label(left, "Quote Outline", pady=(6, 2))
quote_outline_slider = tk.Scale(left, from_=0, to=10, orient="horizontal", label="Width", command=update_quote_outline)
quote_outline_slider.set(2)
quote_outline_slider.pack(fill="x")
tk.Button(left, text="Màu viền của Quote(click)", command=choose_quote_outline_color).pack(fill="x", pady=(4, 10))
make_section_label(left, "Author Outline", pady=(6, 2))
author_outline_slider = tk.Scale(left, from_=0, to=10, orient="horizontal", label="Width", command=update_author_outline)
author_outline_slider.set(2)
author_outline_slider.pack(fill="x")
tk.Button(left, text="Màu viền của Author(click)", command=choose_author_outline_color).pack(fill="x", pady=(4, 10))
make_section_label(left, "Save Settings", pady=(6, 4))
make_section_label(left, "File Name", pady=(0, 4))
save_name_var = tk.StringVar(value="quote_output")
save_name_entry = tk.Entry(left, textvariable=save_name_var, width=34)
save_name_entry.pack(fill="x", pady=(0, 8))
make_section_label(left, "Format", pady=(0, 4))
save_format_var = tk.StringVar(value="png")
tk.OptionMenu(left, save_format_var, "png", "jpg").pack(fill="x", pady=(0, 8))
tk.Button(left, text="Lưu ảnh", command=save_image, bg="#31b267", fg="white", relief="flat").pack(fill="x", pady=(0, 8))
tk.Button(left, text="Copy ảnh", command=copy_image_to_clipboard, bg="#4c8bf5", fg="white", relief="flat").pack(fill="x", pady=(0, 12))
make_section_label(left, "Hướng dẫn format + cách dùng", pady=(6, 4))
admin_notes = tk.Text(left, height=6, wrap="word")
admin_notes.pack(fill="x", pady=(0, 10))
admin_notes.insert("1.0", "- Dùng **<text>** để in đậm chữ\n- Dùng __<text>__ để in nghiêng chữ\n- Dùng \\n để xuống dòng\n- Kéo dấu + để đổi vị trí quote/author\nREALLY BY FORGOTTEN\nThank you for using my tools :>")
for entry in (quote_x_entry, quote_y_entry):
    entry.bind("<Return>", apply_quote_position)
for entry in (author_x_entry, author_y_entry):
    entry.bind("<Return>", apply_author_position)
preview_label.bind("<Button-1>", start_drag)
preview_label.bind("<B1-Motion>", drag)
preview_label.bind("<ButtonRelease-1>", stop_drag)
update_preview()
root.mainloop()
