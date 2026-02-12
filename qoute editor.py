import tkinter as tk
from tkinter import filedialog, colorchooser
from PIL import Image, ImageDraw, ImageFont, ImageTk
import textwrap

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


FONT_PATHS = {
    "Times New Roman": r"C:\Windows\Fonts\times.ttf",
    "Calibri": r"C:\Windows\Fonts\calibri.ttf"
}

def get_font(name, size):
    try:
        return ImageFont.truetype(FONT_PATHS[name], size)
    except:
        return ImageFont.load_default()

def wrap_text(text):
    return "\n".join(textwrap.wrap(text, width=MAX_WIDTH))

def draw_text_with_outline(draw, pos, text, font, fill):
    x, y = pos
    # Vẽ viền
    for dx in range(-outline_width, outline_width+1):
        for dy in range(-outline_width, outline_width+1):
            if dx != 0 or dy != 0:
                draw.multiline_text((x+dx, y+dy), text,
                                    font=font,
                                    fill=outline_color)
    # Vẽ chữ chính
    draw.multiline_text((x, y), text,
                        font=font,
                        fill=fill)


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

def update_preview(*args):
    global preview_img, final_image

    quote = quote_entry.get()
    author = author_entry.get()

    img = Image.open(BG_PATH).copy()
    draw = ImageDraw.Draw(img)

    quote_font = get_font(quote_font_var.get(), quote_size.get())
    author_font = get_font(author_font_var.get(), author_size.get())

    wrapped = wrap_text(quote)
    quote_text = f'"{wrapped}"'
    author_text = f'-{author}-'

    draw_text_with_outline(draw, tuple(quote_pos),
                           quote_text, quote_font, quote_color)

    draw_text_with_outline(draw, tuple(author_pos),
                           author_text, author_font, author_color)

    # ==== DRAW HANDLE (circular + icon) ====
    draw_handle(draw, tuple(quote_pos), fill="#ff5a5f")
    draw_handle(draw, tuple(author_pos), fill="#1f8ef1")

    final_image = img

    preview = img.resize((PREVIEW_W, PREVIEW_H))
    preview_img = ImageTk.PhotoImage(preview)
    preview_label.config(image=preview_img)


def save_image():
    file = filedialog.asksaveasfilename(defaultextension=".png")
    if file:
        final_image.save(file)

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
root.geometry("1100x600")

main = tk.Frame(root)
main.pack(fill="both", expand=True)

left = tk.Frame(main, width=300)
left.pack(side="left", fill="y")

right = tk.Frame(main)
right.pack(side="right", fill="both", expand=True)

preview_label = tk.Label(right)
preview_label.pack(expand=True)

# ==== SELECT MOVE TARGET ====

# ==== INPUT ====
tk.Label(left, text="Quote").pack()
quote_entry = tk.Entry(left, width=30)
quote_entry.pack()
quote_entry.bind("<KeyRelease>", update_preview)

tk.Label(left, text="Author").pack()
author_entry = tk.Entry(left, width=30)
author_entry.pack()
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
          command=choose_quote_color).pack()

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
          command=choose_author_color).pack()

# ==== OUTLINE SETTINGS ====
tk.Label(left, text="Outline Width").pack()
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
          command=choose_outline_color).pack()
tk.Button(left, text="Save Image",
          command=save_image).pack(pady=10)

# ==== LOAD BG ====
bg = Image.open(BG_PATH)
original_w, original_h = bg.size
preview_label.bind("<Button-1>", start_drag)
preview_label.bind("<B1-Motion>", drag)
preview_label.bind("<ButtonRelease-1>", stop_drag)
update_preview()
root.mainloop()