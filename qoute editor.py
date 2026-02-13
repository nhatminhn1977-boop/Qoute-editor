import tkinter as tk
from tkinter import colorchooser, messagebox
from PIL import Image, ImageDraw, ImageFont, ImageTk
import textwrap
import os

BG_PATH = "background.jpg"
PREVIEW_W = 700
PREVIEW_H = 450
MAX_WIDTH = 40
drag_target = None
handle_radius = 14

quote_pos = [150, 200]
author_pos = [200, 300]

quote_color = "white"
author_color = "white"
outline_color = "black"
outline_width = 2

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

    # fallback an toàn để tránh ký tự lạ bị ô vuông quá nhiều
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()


def normalize_input_text(text):
    # cho phép user gõ "\\n" để xuống dòng thủ công
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
    # hỗ trợ **bold** và __italic__
    runs = []
    i = 0

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


def draw_segment_with_outline(draw, x, y, text, font, fill):
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), text, font=font, fill=outline_color)

    draw.text((x, y), text, font=font, fill=fill)


def draw_formatted_text_with_outline(draw, pos, text, font_name, font_size, fill):
    x, y = pos
    line_height = get_line_height(font_name, font_size)

    for line_idx, line in enumerate(text.split("\n")):
        cursor_x = x
        cursor_y = y + line_idx * line_height
        runs = parse_inline_styles(line)

        if not runs:
            continue

        for segment, style in runs:
            if not segment:
                continue

            font = get_font(font_name, font_size, style)
            draw_segment_with_outline(draw, cursor_x, cursor_y, segment, font, fill)
            seg_box = font.getbbox(segment)
            seg_width = seg_box[2] - seg_box[0]
            cursor_x += seg_width


def draw_handle(draw, center, fill, icon_color="white"):
    cx, cy = center
    r = handle_radius

    # vòng tròn chính
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=fill)

    # viền nhẹ để nổi bật trên mọi nền
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline="white", width=2)

    # icon dấu cộng
    plus_half = max(4, r // 2)
    line_w = 3
    draw.line([cx - plus_half, cy, cx + plus_half, cy], fill=icon_color, width=line_w)
    draw.line([cx, cy - plus_half, cx, cy + plus_half], fill=icon_color, width=line_w)


def point_in_handle(point_x, point_y, center_x, center_y):
    dx = point_x - center_x
    dy = point_y - center_y
    return (dx * dx + dy * dy) <= (handle_radius * handle_radius)


def render_canvas_image(show_handles=True):
    quote = quote_entry.get()
    author = author_entry.get()

    img = Image.open(BG_PATH).copy()
    draw = ImageDraw.Draw(img)

    quote_text = format_quote_text(quote)
    author_text = build_author_text(author)

    draw_formatted_text_with_outline(
        draw,
        tuple(quote_pos),
        quote_text,
        quote_font_var.get(),
        quote_size.get(),
        quote_color,
    )

    draw_formatted_text_with_outline(
        draw,
        tuple(author_pos),
        author_text,
        author_font_var.get(),
        author_size.get(),
        author_color,
    )

    if show_handles:
        # ==== DRAW HANDLE (circular + icon) ====
        draw_handle(draw, tuple(quote_pos), fill="#ff5a5f")
        draw_handle(draw, tuple(author_pos), fill="#1f8ef1")

    return img


def update_preview(*args):
    global preview_img, final_image

    final_image = render_canvas_image(show_handles=False)
    preview_image = render_canvas_image(show_handles=True)

    preview = preview_image.resize((PREVIEW_W, PREVIEW_H))
    preview_img = ImageTk.PhotoImage(preview)
    preview_label.config(image=preview_img)


def save_image():
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


def start_drag(event):
    global drag_target

    scale_x = original_w / PREVIEW_W
    scale_y = original_h / PREVIEW_H

    mx = int(event.x * scale_x)
    my = int(event.y * scale_y)

    # check quote handle
    if point_in_handle(mx, my, quote_pos[0], quote_pos[1]):
        drag_target = "quote"

    # check author handle
    elif point_in_handle(mx, my, author_pos[0], author_pos[1]):
        drag_target = "author"
    else:
        drag_target = None


def drag(event):
    global drag_target

    if not drag_target:
        return

    scale_x = original_w / PREVIEW_W
    scale_y = original_h / PREVIEW_H

    if drag_target == "quote":
        quote_pos[0] = int(event.x * scale_x)
        quote_pos[1] = int(event.y * scale_y)
    else:
        author_pos[0] = int(event.x * scale_x)
        author_pos[1] = int(event.y * scale_y)

    update_preview()


def stop_drag(event):
    global drag_target
    drag_target = None




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


def choose_outline_color():
    global outline_color
    c = colorchooser.askcolor()[1]
    if c:
        outline_color = c
        update_preview()


# ===== UI =====
root = tk.Tk()
root.title("🔥 Quote Editor ADVANCED")
root.geometry("1180x680")
root.configure(bg="#1f2430")

main = tk.Frame(root, bg="#1f2430")
main.pack(fill="both", expand=True)

left = tk.Frame(main, width=320, bg="#2a3142", padx=12, pady=12)
left.pack(side="left", fill="y")

right = tk.Frame(main, bg="#1f2430")
right.pack(side="right", fill="both", expand=True)

preview_label = tk.Label(right, bd=0, highlightthickness=0)
preview_label.pack(expand=True)

# ==== INPUT ====
tk.Label(left, text="Quote", bg="#2a3142", fg="white", anchor="w").pack(fill="x", pady=(0, 4))
quote_entry = tk.Entry(left, width=34)
quote_entry.pack(fill="x", pady=(0, 10))
quote_entry.bind("<KeyRelease>", update_preview)

tk.Label(left, text="Author", bg="#2a3142", fg="white", anchor="w").pack(fill="x", pady=(0, 4))
author_entry = tk.Entry(left, width=34)
author_entry.pack(fill="x", pady=(0, 8))
author_entry.bind("<KeyRelease>", update_preview)


# ==== FONT SETTINGS ====
quote_font_var = tk.StringVar(value="Times New Roman")
author_font_var = tk.StringVar(value="Times New Roman")

tk.OptionMenu(left, quote_font_var,
              "Times New Roman", "Calibri",
              command=update_preview).pack()

quote_size = tk.Scale(left, from_=20, to=100,
                      orient="horizontal",
                      label="Quote Size",
                      command=update_preview)
quote_size.set(40)
quote_size.pack()

tk.Button(left, text="Quote Color",
          command=choose_quote_color).pack(fill="x", pady=(4, 10))

tk.OptionMenu(left, author_font_var,
              "Times New Roman", "Calibri",
              command=update_preview).pack()

author_size = tk.Scale(left, from_=15, to=80,
                       orient="horizontal",
                       label="Author Size",
                       command=update_preview)
author_size.set(30)
author_size.pack()

tk.Button(left, text="Author Color",
          command=choose_author_color).pack(fill="x", pady=(4, 10))


# ==== SAVE SETTINGS ====
tk.Label(left, text="File Name", bg="#2a3142", fg="white", anchor="w").pack(fill="x", pady=(6, 4))
save_name_var = tk.StringVar(value="quote_output")
save_name_entry = tk.Entry(left, textvariable=save_name_var, width=34)
save_name_entry.pack(fill="x", pady=(0, 8))

tk.Label(left, text="Format", bg="#2a3142", fg="white", anchor="w").pack(fill="x", pady=(0, 4))
save_format_var = tk.StringVar(value="png")
tk.OptionMenu(left, save_format_var, "png", "jpg").pack(fill="x", pady=(0, 8))

tk.Button(left, text="Save Image",
          command=save_image, bg="#31b267", fg="white", relief="flat").pack(fill="x", pady=(0, 12))

# ==== ADMIN NOTES ====
tk.Label(left, text="Admin Notes / Usage", bg="#2a3142", fg="white", anchor="w").pack(fill="x", pady=(6, 4))
admin_notes = tk.Text(left, height=6, wrap="word")
admin_notes.pack(fill="x", pady=(0, 10))
admin_notes.insert("1.0", "- Dùng **text** để in đậm\n- Dùng __text__ để in nghiêng\n- Dùng \\n để xuống dòng\n- Kéo dấu + để đổi vị trí quote/author")

# ==== OUTLINE SETTINGS ====
tk.Label(left, text="Outline Width", bg="#2a3142", fg="white", anchor="w").pack(fill="x", pady=(6, 2))
outline_slider = tk.Scale(left, from_=0, to=10,
                          orient="horizontal",
                          command=lambda x: update_preview())
outline_slider.set(2)
outline_slider.pack()


def update_outline(val):
    global outline_width
    outline_width = int(val)
    update_preview()


outline_slider.config(command=update_outline)
tk.Button(left, text="Outline Color",
          command=choose_outline_color).pack(fill="x", pady=(4, 8))

# ==== LOAD BG ====
bg = Image.open(BG_PATH)
original_w, original_h = bg.size
preview_label.bind("<Button-1>", start_drag)
preview_label.bind("<B1-Motion>", drag)
preview_label.bind("<ButtonRelease-1>", stop_drag)
update_preview()
root.mainloop()